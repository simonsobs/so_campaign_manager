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

    campaign_dag = DAG()
    last_workflow_id = 1
    for workflow_name, workflow_config in config['stages'].items():

        if workflow_name not in registered_workflows:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. Known: {sorted(registered_workflows)}"
            )

        workflow_config["resources"]["memory"] = (
                humanfriendly.parse_size(workflow_config["resources"]["memory"])
                // 1000000
            )
        workflow_config["resources"]["runtime"] = (
                humanfriendly.parse_timespan(workflow_config["resources"]["runtime"])
                / 60
            )  # in minutes


        if "base-path" in workflow_config and workflow_config["base-path"]:
            workflow_config["base_path"] = workflow_config["base-path"]
        elif "base-path" in config["campaign"] and config["campaign"]["base-path"]:
            workflow_config["base_path"] = config["campaign"]["base-path"]
        workflow_factory = registered_workflows[workflow_name]
        # Values from a par file are defaults; the stage config overrides them.
        par_file = workflow_config.pop("param-file", None)
        if par_file:
            par_path = Path(par_file.removeprefix("file://"))
            if not par_path.is_absolute():
                par_path = Path(args.yaml).parent / par_path
            workflow_config = {**read_par_file(par_path), **workflow_config}
        for arg_name, arg_value in workflow_config.get('script-kwargs', {}).items():
            workflow_config[arg_name] = arg_value
        workflow_config["id"] = last_workflow_id
        workflow = workflow_factory(**workflow_config)

        campaign_dag.add_workflow(workflow)
        last_workflow_id += 1

    for workflow in campaign_dag.workflows:
        for parent_workflow in workflow.depends:
            parent_id = campaign_dag.get_id_by_name(workflow_name=parent_workflow)
            campaign_dag.add_dependency(child_id=workflow.id, parent_id=parent_id)

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
