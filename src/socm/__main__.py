import toml
from argparse import ArgumentParser

from socm.workflows import registered_workflows

def get_parser() -> ArgumentParser:
    """Create and return the argument parser for the SO campaign."""
    parser = ArgumentParser(description="Run the SO campaign.")
    parser.add_argument(
        "--toml", "-t",
        type=str,
        required=True,
        help="Path to the configuration file for the workflow.",
    )
    return parser


def main()-> None:
    parser = get_parser()
    args = parser.parse_args()
    config = toml.load(args.toml)
    workflow_types = config["campaign"].keys()
    workflows = []
    for workflow_type in workflow_types:
        if workflow_type in registered_workflows:
            workflow = registered_workflows[workflow_type](**config["campaign"][workflow_type])
            workflows.append(workflow)

    print(f"Workflows to run: {workflows}")
