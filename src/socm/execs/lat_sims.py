from argparse import ArgumentParser, Namespace
from pathlib import Path

import humanfriendly
import yaml

from socm.core.models import DAG, Campaign
from socm.utils.misc import read_par_file
from socm.workflows import registered_workflows


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
    return str(path)


def build_dag(config: dict, config_dir: Path) -> DAG:
    """
    Build the campaign DAG from the ``stages`` section of a YAML config.

    Each stage creates one workflow named after the stage. The workflow type
    is the stage's ``type`` key, or the stage name when ``type`` is not given,
    so several stages can share a type (e.g. ``shell-script``).

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
    last_workflow_id = 1
    for stage_name, workflow_config in config['stages'].items():
        workflow_type = workflow_config.pop("type", stage_name)
        if workflow_type not in registered_workflows:
            raise ValueError(
                f"Stage '{stage_name}': unknown workflow type '{workflow_type}'. "
                f"Known: {sorted(registered_workflows)}"
            )

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
        workflow_factory = registered_workflows[workflow_type]
        # Values from a par file are defaults; the stage config overrides them.
        par_file = workflow_config.pop("param-file", None)
        if par_file:
            workflow_config = {**read_par_file(_resolve_path(par_file, config_dir)), **workflow_config}
        if "script" in workflow_config:
            workflow_config["script"] = _resolve_path(workflow_config["script"], config_dir)
        for arg_name, arg_value in workflow_config.get('script-kwargs', {}).items():
            workflow_config[arg_name] = arg_value
        workflow_config["id"] = last_workflow_id
        workflow_config["name"] = stage_name
        workflow = workflow_factory(**workflow_config)

        campaign_dag.add_workflow(workflow)
        last_workflow_id += 1

    for workflow in campaign_dag.workflows:
        for parent_workflow in workflow.depends:
            parent_id = campaign_dag.get_id_by_name(workflow_name=parent_workflow)
            if parent_id is None:
                raise ValueError(f"Stage '{workflow.name}' depends on unknown stage '{parent_workflow}'")
            campaign_dag.add_dependency(child_id=workflow.id, parent_id=parent_id)

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
