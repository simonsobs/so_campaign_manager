import copy
import itertools
from argparse import ArgumentParser, Namespace
from pathlib import Path
from string import Template
from typing import Any

import humanfriendly
import yaml

from socm.core.models import DAG, Campaign, Workflow
from socm.utils.misc import read_par_file
from socm.workflows import registered_workflows

# Stage keys that keep their matrix placeholders as written.
_NOT_SUBSTITUTED = {"type", "depends"}


def get_parser(parser: ArgumentParser) -> ArgumentParser:
    """
    Add mapmaking subcommand arguments to the given parser.

    Parameters
    ----------
    parser : ArgumentParser
        The subparser to configure with mapmaking-specific arguments.

    Returns
    -------
    ArgumentParser
        The configured argument parser.
    """
    parser.add_argument(
        "--yaml",
        "-y",
        type=str,
        required=True,
        help="Path to the configuration file that describes the campaign.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enable dry run for faster development. This flag does not actually run the campaign.",
    )
    return parser


def _resolve_path(value: str, config_dir: Path) -> str:
    """Resolve a (possibly ``file://``) path relative to the config file's directory."""
    path = Path(value.removeprefix("file://"))
    if not path.is_absolute():
        path = config_dir / path
    # Absolute, because tasks run in their own sandbox, not where socm was started.
    return str(path.resolve())


def _substitute(value: Any, variables: dict[str, Any]) -> Any:
    """
    Fill ``${var}`` placeholders in every string of ``value`` (nested dicts and
    lists included). Unknown names such as ``$SCRATCH`` are left as they are,
    and so is toast's own ``{wafer_slot}`` placeholder.
    """
    if isinstance(value, str):
        return Template(value).safe_substitute(variables)
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, variables) for v in value]
    return value


def _expand_matrix(stage_name: str, stage_config: dict) -> list[tuple[str, dict[str, Any], dict]]:
    """
    Expand a stage into one workflow config per combination of its ``matrix``.

    The matrix maps axis names to lists of values and expands to their
    cartesian product, in key order. A value can be a mapping: all its keys
    become variables, and its own ``axis`` key is the axis value. Each config
    is a copy of the stage with ``${var}`` filled in, except in ``type`` and
    ``depends``.

    Parameters
    ----------
    stage_name : str
        Name of the stage; workflows are named ``<stage>.<v1>.<v2>...``.
    stage_config : dict
        The stage from the YAML config. It is not modified.

    Returns
    -------
    list of (str, dict, dict)
        Workflow name, axis values and workflow config for each combination.
        A stage without a matrix gives a single entry named after the stage.
    """
    matrix = stage_config.get("matrix")
    if not matrix:
        return [(stage_name, {}, copy.deepcopy(stage_config))]
    if not isinstance(matrix, dict) or not all(isinstance(v, list) and v for v in matrix.values()):
        raise ValueError(f"Stage '{stage_name}': matrix must map axis names to non-empty lists")

    instances = []
    for combination in itertools.product(*matrix.values()):
        axis_values: dict[str, Any] = {}
        variables: dict[str, Any] = {}
        for axis, value in zip(matrix, combination, strict=True):
            if isinstance(value, dict):
                if axis not in value:
                    raise ValueError(f"Stage '{stage_name}': every '{axis}' row of the matrix must set '{axis}'")
                variables.update(value)
                value = value[axis]
            axis_values[axis] = value
        variables.update(axis_values)

        workflow_config = {
            key: value if key in _NOT_SUBSTITUTED else _substitute(value, variables)
            for key, value in stage_config.items()
            if key != "matrix"
        }
        name = ".".join([stage_name, *(str(v) for v in axis_values.values())])
        instances.append((name, axis_values, copy.deepcopy(workflow_config)))
    return instances


def _build_workflow(
    workflow_factory: type[Workflow],
    workflow_config: dict,
    config: dict,
    config_dir: Path,
    workflow_id: int,
    name: str,
) -> Workflow:
    """Turn one expanded stage config into a workflow. ``workflow_config`` is modified."""
    workflow_config.pop("type", None)
    workflow_config["resources"]["memory"] = (
            humanfriendly.parse_size(workflow_config["resources"]["memory"])
            // 1000000
        )
    workflow_config["resources"]["runtime"] = (
            humanfriendly.parse_timespan(workflow_config["resources"]["runtime"])
            / 60
        )  # in minutes

    stage_base_path = workflow_config.pop("base-path", None)
    if stage_base_path:
        workflow_config["base_path"] = stage_base_path
    elif config["campaign"].get("base-path"):
        workflow_config["base_path"] = config["campaign"]["base-path"]
    # Values from a par file are defaults; the stage config overrides them.
    par_file = workflow_config.pop("param-file", None)
    if par_file:
        workflow_config = {**read_par_file(_resolve_path(par_file, config_dir)), **workflow_config}
    if "script" in workflow_config:
        workflow_config["script"] = _resolve_path(workflow_config["script"], config_dir)
    for arg_name, arg_value in workflow_config.pop('script-kwargs', {}).items():
        workflow_config[arg_name] = arg_value

    workflow_config["id"] = workflow_id
    workflow_config["name"] = name
    workflow_config["depends"] = workflow_config.get("depends") or []
    return workflow_factory(**workflow_config)


def build_dag(config: dict, config_dir: Path) -> DAG:
    """
    Build the campaign DAG from the ``stages`` section of a YAML config.

    Each stage creates one workflow named after the stage, or, with a
    ``matrix``, one workflow per combination of the matrix values. The
    workflow type is the stage's ``type`` key, or the stage name when
    ``type`` is not given, so several stages can share a type (e.g.
    ``shell-script``).

    ``depends`` names stages. A workflow depends on the workflows of each
    parent stage that have the same values on the matrix axes both stages
    share, so a ``comp`` run with ``split``, ``band`` and ``tube`` axes waits
    only for the noise run of its own split, band and tube. With no shared
    axes it depends on all of them. The workflow's ``depends`` is set to the
    names of those workflows. The config is not modified.

    Parameters
    ----------
    config : dict
        The parsed YAML configuration.
    config_dir : Path
        Directory of the YAML file; relative ``param-file`` and ``script``
        paths are resolved against it.

    Returns
    -------
    DAG
        The workflows with their dependencies.
    """
    campaign_dag = DAG()
    stages: dict[str, list[tuple[Workflow, dict[str, Any]]]] = {}
    names: set[str] = set()
    workflow_id = 1
    for stage_name, stage_config in config['stages'].items():
        workflow_type = stage_config.get("type", stage_name)
        if workflow_type not in registered_workflows:
            raise ValueError(
                f"Stage '{stage_name}': unknown workflow type '{workflow_type}'. "
                f"Known: {sorted(registered_workflows)}"
            )

        stages[stage_name] = []
        for name, axis_values, workflow_config in _expand_matrix(stage_name, stage_config):
            if name in names:
                raise ValueError(f"Stage '{stage_name}': more than one workflow is named '{name}'")
            names.add(name)
            workflow = _build_workflow(
                registered_workflows[workflow_type], workflow_config, config, config_dir, workflow_id, name
            )
            campaign_dag.add_workflow(workflow)
            stages[stage_name].append((workflow, axis_values))
            workflow_id += 1

    for stage_name, instances in stages.items():
        for workflow, axis_values in instances:
            parents = []
            for parent_stage in workflow.depends:
                if parent_stage not in stages:
                    raise ValueError(f"Stage '{stage_name}' depends on unknown stage '{parent_stage}'")
                matching = [
                    parent
                    for parent, parent_values in stages[parent_stage]
                    if all(str(parent_values[axis]) == str(value)
                           for axis, value in axis_values.items() if axis in parent_values)
                ]
                if not matching:
                    raise ValueError(f"Workflow '{workflow.name}' matches no workflow of stage '{parent_stage}'")
                parents.extend(matching)
            for parent in parents:
                campaign_dag.add_dependency(child_id=workflow.id, parent_id=parent.id)
            # The planner and Campaign match dependencies by workflow name.
            workflow.depends = [parent.name for parent in parents]

    return campaign_dag


def _main(args: Namespace) -> None:
    """
    Execute the power spectra campaign from a YAML configuration.

    Parses the YAML config, creates workflow instances, builds a campaign
    DAG, and runs the campaign through the Bookkeeper.

    Parameters
    ----------
    args : Namespace
        Parsed command-line arguments containing ``yaml`` and ``dry_run``.
    """
    # Import here to avoid loading radical.pilot at CLI startup (not available on macOS)
    from socm.bookkeeper import Bookkeeper

    with open(args.yaml) as f:
        config = yaml.safe_load(f)

    campaign_dag = build_dag(config, Path(args.yaml).parent)

    policy = config["campaign"].get("policy", "time")
    target_resource = config["campaign"].get("resource", "tiger3")

    campaign = Campaign(
        id=1,
        workflows=campaign_dag,
        campaign_policy=policy,
        deadline=config["campaign"]["deadline"],
        execution_schema=config["campaign"]["execution_schema"],
        requested_resources=config["campaign"]["requested_resources"],
        target_resource=target_resource,
        base_path=config["campaign"].get("base-path"),
    )

    # This main class to execute the campaign to a resource.
    b = Bookkeeper(
        campaign=campaign,
        policy=policy,
        target_resource=target_resource,
        deadline=humanfriendly.parse_timespan(config["campaign"]["deadline"]) / 60,
        dryrun=args.dry_run
    )

    b.run()
