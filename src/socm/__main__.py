from argparse import ArgumentParser

import humanfriendly
import toml

from socm.bookkeeper import Bookkeeper
from socm.core.models import Campaign
from socm.utils.misc import get_workflow_entries
from socm.workflows import registered_workflows, subcampaign_map


def get_parser() -> ArgumentParser:
    """Create and return the argument parser for the SO campaign."""
    parser = ArgumentParser(description="Run the SO campaign.")
    parser.add_argument(
        "--toml",
        "-t",
        type=str,
        required=True,
        help="Path to the configuration file for the workflow.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enable dry run for faster development. This flag does not actually run the campaign.",
    )
    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    config = toml.load(args.toml)
    workflows_configs = get_workflow_entries(config, subcampaign_map=subcampaign_map)

    workflows = []
    for workflow_type, workflow_config in workflows_configs.items():
        if workflow_type in registered_workflows:
            workflow_config["resources"]["memory"] = (
                humanfriendly.parse_size(workflow_config["resources"]["memory"])
                // 1000000
            )
            workflow_config["resources"]["runtime"] = (
                humanfriendly.parse_timespan(workflow_config["resources"]["runtime"])
                / 60
            )  # in minutes
            workflow_factory = registered_workflows[workflow_type]
            tmp_workflows = workflow_factory.get_workflows(workflow_config)
            for workflow in tmp_workflows:
                workflow.id = len(workflows) + 1  # Assign a unique ID to each workflow
                workflows.append(workflow)

    policy  = config["campaign"].get("policy","time")
    target_resource = config["campaign"].get("resource","tiger3")
    # pprint(workflows)
    campaign = Campaign(
        id=1,
        workflows=workflows,
        campaign_policy=policy,
        deadline=config["campaign"]["deadline"],
        execution_schema=config["campaign"]["execution_schema"],
        requested_resources=config["campaign"]["requested_resources"],
        target_resource=target_resource,
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
