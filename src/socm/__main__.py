import toml
from argparse import ArgumentParser

import radical.utils as ru

from socm.workflows import registered_workflows
from socm.bookkeeper import Bookkeeper
from socm.core import Campaign, Resource


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
    return parser


def main() -> None:
    logger = ru.Logger("SOCM", level="debug")
    parser = get_parser()
    args = parser.parse_args()
    config = toml.load(args.toml)
    workflow_types = config["campaign"].keys()
    workflows = []
    for workflow_type in workflow_types:
        if workflow_type in registered_workflows:
            # TODO: this can be a list of workflows, not just one.
            workflow = registered_workflows[workflow_type](
                **config["campaign"][workflow_type]
            )
            workflow.id = len(workflows) + 1  # Assign a unique ID to each workflow
            workflows.append(workflow)

    campaign = Campaign(
        id=1,
        workflows=workflows,
        campaign_policy="time",
    )

    # A resource is where the campaign will run.
    resource = Resource(
        name="tiger3",
        nodes=1,
        cores_per_node=112,
        memory_per_node=100000000,
        default_queue="tiger-test",
        maximum_walltime=3600000,
    )

    # This main class to execute the campaign to a resource.
    b = Bookkeeper(
        campaign=campaign,
        resources={"tiger3": resource},
        policy="time",
        target_resource="tiger3",
    )

    b.run()
