from argparse import ArgumentParser, Namespace

import humanfriendly
import yaml

from socm.core.models import DAG, Campaign, Workflow


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
    # from socm.bookkeeper import Bookkeeper

    with open('examples/dag.yml') as f:
        config = yaml.safe_load(f)

    campaign_dag = DAG()
    last_workflow_id = 1
    for workflow_name, workflow_config in config['stages'].items():
        workflow_config["resources"]["memory"] = (
                humanfriendly.parse_size(workflow_config["resources"]["memory"])
                // 1000000
            )
        workflow_config["resources"]["runtime"] = (
                humanfriendly.parse_timespan(workflow_config["resources"]["runtime"])
                / 60
            )  # in minutes
        workflow_dict = {"name": workflow_name,
                         "id": last_workflow_id,
                         "executable": workflow_config['executable'],
                         "subcommand": workflow_config['script'],
                         "depends": workflow_config['depends'],
                         "resources": workflow_config["resources"],
                         }

        for arg_name, arg_value in workflow_config['script-kargs'].items():
            workflow_dict[arg_name] = arg_value

        workflow = Workflow(**workflow_dict)

        campaign_dag.add_workflow(workflow)
        if workflow.depends:
            for parent_workflow in workflow.depends:
                parent_id = campaign_dag.get_id_by_name(workflow_name=parent_workflow)
                campaign_dag.add_dependency(child_id=last_workflow_id, parent_id=parent_id)

    policy = config["campaign"].get("policy", "time")
    target_resource = config["campaign"].get("resource", "tiger3")
    # pprint(workflows)
    campaign = Campaign(
        id=1,
        workflows=campaign_dag,
        campaign_policy=policy,
        deadline=config["campaign"]["deadline"],
        execution_schema=config["campaign"]["execution_schema"],
        requested_resources=config["campaign"]["requested_resources"],
        target_resource=target_resource,
    )
    # breakpoint()
    print(campaign)
    # This main class to execute the campaign to a resource.
    # b = Bookkeeper(
    #     campaign=campaign,
    #     policy=policy,
    #     target_resource=target_resource,
    #     deadline=humanfriendly.parse_timespan(config["campaign"]["deadline"]) / 60,
    #     dryrun=args.dry_run
    # )

    # b.run()
