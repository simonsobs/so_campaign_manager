import copy
from pathlib import Path

import pytest
import yaml

from socm.execs.lat_sims import build_dag
from socm.workflows import GetScheduleWorkflow, LATSimWorkflow, ShellScriptWorkflow

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


def test_null_or_missing_depends(tmp_path):
    stages = {
        "a": _shell_stage("/a.sh", depends=None),
        "b": _shell_stage("/b.sh"),  # no depends key
        "c": _shell_stage("/c.sh", depends=["a", "b"]),
    }
    dag = build_dag(_config(stages), tmp_path)
    by_name = {w.name: w for w in dag.workflows}

    assert by_name["a"].depends == []
    assert by_name["b"].depends == []
    assert by_name["c"].depends == ["a", "b"]
    assert dag.graph.has_edge(by_name["a"].id, by_name["c"].id)
    assert dag.graph.has_edge(by_name["b"].id, by_name["c"].id)


def test_script_kwargs_are_expanded_not_passed(tmp_path):
    stage = _shell_stage("/a.sh", **{"script-kwargs": {"extra": "value"}})
    workflow = build_dag(_config({"stage": stage}), tmp_path).workflows[0]

    assert workflow.extra == "value"
    assert "script-kwargs" not in workflow.model_dump()


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


def test_lat_sims_stage_with_par_file(tmp_path):
    """A lat-sims stage reads its par file; stage keys override par file values."""
    (tmp_path / "noise.par").write_text(
        "--sim_noise.enable\n"
        "--mlmapmaker.nmat_mode=cache\n"
        "--sort_schedule\n"
    )
    stage = {
        "type": "lat-sims",
        "param-file": "./noise.par",
        "output_dir": "/scratch/LAT_f090/i6/split_1/noise",
        "bands": "LAT_f090",
        "tube_slots": "i6",
        "mlmapmaker.nmat_mode": "load",
        "resources": {"memory": "1G", "ranks": 272, "threads": 7, "runtime": "40h"},
    }
    dag = build_dag(_config({"lat-noise": stage}), tmp_path)
    (workflow,) = dag.workflows
    arguments = workflow.get_arguments()

    assert isinstance(workflow, LATSimWorkflow)
    assert workflow.name == "lat-noise"
    assert "--sim_noise.enable" in arguments
    assert "--sort_schedule" in arguments
    assert "--mlmapmaker.nmat_mode=load" in arguments  # stage wins
    assert "--mlmapmaker.nmat_mode=cache" not in arguments
    assert "--tube_slots=i6" in arguments


MID_BANDS = [
    {"band": "LAT_f090", "cmn_alpha": "2.654"},
    {"band": "LAT_f150", "cmn_alpha": "2.744"},
]


def _lat_stage(matrix, **extra):
    return {
        "type": "lat-sims",
        "matrix": matrix,
        "output_dir": "/out/${band}/split_${split}",
        "resources": dict(RESOURCES),
        **extra,
    }


def _parents(dag, workflow):
    by_id = {w.id: w for w in dag.workflows}
    return sorted(by_id[i].name for i in dag.graph.predecessors(workflow.id))


def test_matrix_expands_to_one_workflow_per_combination(tmp_path):
    stage = _lat_stage(
        {"split": [1, 2], "tube": ["i6", "i1"], "band": MID_BANDS},
        schedule="/s/schedule.${split}.txt",
        tube_slots="${tube}",
        bands="${band}",
        operators={
            "common_mode_noise": {"enable": True, "alpha": "${cmn_alpha}"},
            "scan_alm": {"enable": True, "file": "$SCRATCH/maps/{wafer_slot}_${band}.fits"},
        },
    )
    dag = build_dag(_config({"lat-noise": stage}), tmp_path)
    by_name = {w.name: w for w in dag.workflows}

    assert len(by_name) == 8
    assert "lat-noise.1.i6.LAT_f090" in by_name
    arguments = by_name["lat-noise.2.i1.LAT_f150"].get_arguments()
    assert arguments[:2] == ["--out", "/out/LAT_f150/split_2"]
    assert "--schedule=/s/schedule.2.txt" in arguments
    assert "--tube_slots=i1" in arguments
    assert "--common_mode_noise.alpha=2.744" in arguments  # from the matrix row
    # Unknown names and toast's own placeholder are left alone.
    assert "--scan_alm.file=$SCRATCH/maps/{wafer_slot}_LAT_f150.fits" in arguments
    # Matrix variables are not workflow options.
    assert not any(arg.startswith(("--split", "--tube=", "--band=", "--cmn_alpha")) for arg in arguments)


def test_signal_runs_depend_on_their_own_noise_run(tmp_path):
    stages = {
        "split-schedule": _shell_stage("split.sh"),
        "lat-noise": _lat_stage({"split": [1, 2], "band": MID_BANDS}, depends=["split-schedule"]),
        "lat-signal": _lat_stage(
            {"split": [1, 2], "band": MID_BANDS, "comp": ["cmb", "foreground"]}, depends=["lat-noise"]
        ),
    }
    dag = build_dag(_config(stages), tmp_path)
    by_name = {w.name: w for w in dag.workflows}

    for name in ("lat-noise.1.LAT_f090", "lat-noise.2.LAT_f150"):
        assert _parents(dag, by_name[name]) == ["split-schedule"]
        assert by_name[name].depends == ["split-schedule"]
    signal = by_name["lat-signal.2.LAT_f090.foreground"]
    assert _parents(dag, signal) == ["lat-noise.2.LAT_f090"]
    # The planner and Campaign look dependencies up by workflow name.
    assert signal.depends == ["lat-noise.2.LAT_f090"]
    assert all(len(_parents(dag, w)) == 1 for w in dag.workflows if w.name.startswith("lat-signal."))


def test_stage_without_shared_axes_depends_on_every_run(tmp_path):
    stages = {
        "lat-noise": _lat_stage({"split": [1, 2], "band": MID_BANDS}),
        "collect": _shell_stage("collect.sh", depends=["lat-noise"]),
    }
    dag = build_dag(_config(stages), tmp_path)
    collect = next(w for w in dag.workflows if w.name == "collect")

    assert _parents(dag, collect) == sorted(
        f"lat-noise.{split}.{band}" for split in (1, 2) for band in ("LAT_f090", "LAT_f150")
    )


def test_param_file_path_is_substituted(tmp_path):
    (tmp_path / "cmb.par").write_text("--scan_alm.enable\n")
    (tmp_path / "foreground.par").write_text("--scan_alm.disable\n")
    stage = _lat_stage({"comp": ["cmb", "foreground"]}, **{"param-file": "./${comp}.par"})
    by_name = {w.name: w for w in build_dag(_config({"lat-signal": stage}), tmp_path).workflows}

    assert "--scan_alm.enable" in by_name["lat-signal.cmb"].get_arguments()
    assert "--scan_alm.disable" in by_name["lat-signal.foreground"].get_arguments()


def test_unmatched_dependency_raises(tmp_path):
    stages = {
        "lat-noise": _lat_stage({"split": [1, 2]}),
        "lat-signal": _lat_stage({"split": [3]}, depends=["lat-noise"]),
    }
    with pytest.raises(ValueError, match="'lat-signal.3' matches no workflow of stage 'lat-noise'"):
        build_dag(_config(stages), tmp_path)


def test_matrix_row_without_its_axis_key_raises(tmp_path):
    stage = _lat_stage({"band": [{"cmn_alpha": "2.6"}]})
    with pytest.raises(ValueError, match="every 'band' row of the matrix must set 'band'"):
        build_dag(_config({"lat-noise": stage}), tmp_path)


def test_matrix_with_empty_axis_raises(tmp_path):
    with pytest.raises(ValueError, match="non-empty lists"):
        build_dag(_config({"lat-noise": _lat_stage({"split": []})}), tmp_path)


def test_build_dag_does_not_modify_the_config(tmp_path):
    """Building twice gives the same DAG, also with resources shared through a YAML anchor."""
    config = yaml.safe_load(
        "campaign: {deadline: 1h}\n"
        "x-res: &res {memory: 1G, ranks: 1, threads: 1, runtime: 5m}\n"
        "stages:\n"
        "  first: {type: shell-script, script: a.sh, resources: *res}\n"
        "  second: {type: shell-script, script: b.sh, resources: *res}\n"
        "  lat-noise:\n"
        "    type: lat-sims\n"
        "    matrix: {split: [1, 2]}\n"
        "    output_dir: /out/${split}\n"
        "    resources: *res\n"
    )
    snapshot = copy.deepcopy(config)

    first = build_dag(config, tmp_path)
    second = build_dag(config, tmp_path)

    assert config == snapshot
    assert [w.model_dump() for w in first.workflows] == [w.model_dump() for w in second.workflows]
    assert {w.resources.memory for w in first.workflows} == {1000}


def test_relative_config_dir_gives_absolute_script_path(tmp_path, monkeypatch):
    """With ``-y configs/campaign.yml`` the script path must still be absolute for the task sandbox."""
    monkeypatch.chdir(tmp_path)
    dag = build_dag(_config({"split": _shell_stage("scripts/split.sh")}), Path("configs"))

    assert dag.workflows[0].script == str(tmp_path / "configs" / "scripts" / "split.sh")
