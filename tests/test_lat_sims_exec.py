import pytest
import yaml

from socm.execs.lat_sims import build_dag
from socm.workflows import GetScheduleWorkflow, ShellScriptWorkflow

RESOURCES = {"memory": "1G", "ranks": 1, "threads": 1, "runtime": "5m"}


def _config(stages):
    return {"campaign": {"deadline": "1h"}, "stages": stages}


def _shell_stage(script, **extra):
    return {"type": "shell-script", "script": script, "resources": dict(RESOURCES), **extra}


CONFIG_YAML = """\
campaign:
  deadline: 1h
stages:
  get-schedule:
    param-file: ./schedule.par
    resources: {memory: 1G, ranks: 1, threads: 1, runtime: 5m}
  split-schedule:
    type: shell-script
    script: ./scripts/split.sh
    script-args: [/s/full.txt, /s/split]
    depends: [get-schedule]
    resources: {memory: 1G, ranks: 1, threads: 1, runtime: 5m}
"""


def test_yaml_config_with_relative_paths(tmp_path):
    """param-file and script paths in the YAML resolve against the YAML's directory."""
    (tmp_path / "schedule.par").write_text("--out\n/s/full.txt\n--equalize-time\n")
    config_file = tmp_path / "campaign.yml"
    config_file.write_text(CONFIG_YAML)
    with open(config_file) as f:
        config = yaml.safe_load(f)

    dag = build_dag(config, config_file.parent)
    by_name = {w.name: w for w in dag.workflows}

    assert set(by_name) == {"get-schedule", "split-schedule"}
    get_schedule = by_name["get-schedule"]
    assert isinstance(get_schedule, GetScheduleWorkflow)
    assert get_schedule.output_dir == "/s/full.txt"   # from the par file
    split = by_name["split-schedule"]
    assert isinstance(split, ShellScriptWorkflow)
    assert split.get_arguments() == [str(tmp_path / "scripts" / "split.sh"), "/s/full.txt", "/s/split"]
    assert dag.graph.has_edge(get_schedule.id, split.id)


def test_stages_share_a_type(tmp_path):
    dag = build_dag(_config({"first": _shell_stage("a.sh"), "second": _shell_stage("/abs/b.sh")}), tmp_path)
    by_name = {w.name: w for w in dag.workflows}

    assert set(by_name) == {"first", "second"}
    assert by_name["first"].script == str(tmp_path / "a.sh")   # relative to the config dir
    assert by_name["second"].script == "/abs/b.sh"
    assert "type" not in by_name["first"].model_dump()


def test_stage_name_is_type_without_type_key(tmp_path):
    stage = _shell_stage("a.sh")
    del stage["type"]
    dag = build_dag(_config({"shell-script": stage}), tmp_path)
    assert isinstance(dag.workflows[0], ShellScriptWorkflow)


def test_unknown_type_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown workflow type 'nope'"):
        build_dag(_config({"stage": {"type": "nope", "resources": dict(RESOURCES)}}), tmp_path)


def test_unknown_dependency_raises(tmp_path):
    with pytest.raises(ValueError, match="depends on unknown stage 'missing'"):
        build_dag(_config({"stage": _shell_stage("a.sh", depends=["missing"])}), tmp_path)


def test_stage_base_path_is_not_left_as_a_field(tmp_path):
    dag = build_dag(_config({"stage": _shell_stage("a.sh", **{"base-path": "/base"})}), tmp_path)
    workflow = dag.workflows[0]
    assert workflow.base_path == "/base"
    assert "base-path" not in workflow.model_dump()
