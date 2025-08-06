from argparse import ArgumentParser

import toml
from rich.pretty import pprint

from socm.utils.misc import get_workflow_entries
from socm.workflows import registered_workflows, subcampaign_map


def display_banner() -> None:
    """Display the SO LAT mission launched banner with galaxy."""
    banner_lines = [
        "        ✦       🌌      ⭐     ✨         SO LAT MISSION LAUNCHED         ✨     ⭐      🌌       ✦        ",
        "     ✨    🌟        ★           ╭─────────────────────────────────────────────╮           ★        🌟    ✨     ",
        "   ⭐      ∘    ⭐       ●       │           Welcome to SO Campaign           │       ●       ⭐    ∘      ⭐   ",
        "  🌌   ☆     ✦    ★      ◦      │             Manager (socm)                 │      ◦      ★    ✦     ☆   🌌  ",
        "    ∘   ✨     ●   ⭐      ⊙     │         Simmons Observatory                │     ⊙      ⭐   ●     ✨   ∘    ",
        "  ★      ◦    🌟     ∘    ☆     │      Large Aperture Telescope              │     ☆    ∘     🌟    ◦      ★  ",
        "    ●   ⭐      ∘   ★     ◦      │            Ready for launch!               │      ◦     ★   ∘      ⭐   ●    ",
        "   🌌  ✦     ☆     ●     ⊙      ╰─────────────────────────────────────────────╯      ⊙     ●     ☆     ✦  🌌   ",
        "     ✨    ⭐      ★    ∘        ✦       🌌      ⭐     ✨         ★         ✨     ⭐      🌌       ✦        ",
        "        ∘       ●     ☆          Campaign management for cutting-edge astronomy          ☆     ●       ∘        "
    ]
    
    print()
    for line in banner_lines:
        print(line)
    print()


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
    display_banner()
    parser = get_parser()
    args = parser.parse_args()
    config = toml.load(args.toml)
    workflows_configs = get_workflow_entries(config, subcampaign_map=subcampaign_map)
    workflows = []
    for workflow_type, workflow_config in workflows_configs.items():
        if workflow_type in registered_workflows:
            # TODO: this can be a list of workflows, not just one.
            workflow_factory = registered_workflows[workflow_type]
            tmp_workflows = workflow_factory.get_workflows(workflow_config)
            for workflow in tmp_workflows:
                workflow.id = len(workflows) + 1  # Assign a unique ID to each workflow
                workflows.append(workflow)

    pprint(workflows)
    # campaign = Campaign(
    #     id=1,
    #     workflows=workflows,
    #     campaign_policy="time",
    #     deadline=config["campaign"]["deadline"],
    # )

    # A resource is where the campaign will run.
    # resource = Resource(
    #     name="tiger3",
    #     nodes=config["campaign"]["resources"]["nodes"],
    #     cores_per_node=config["campaign"]["resources"]["cores-per-node"],
    #     memory_per_node=100000000,
    #     default_queue="tiger-test",
    #     maximum_walltime=3600000,
    # )

    # # This main class to execute the campaign to a resource.
    # b = Bookkeeper(
    #     campaign=campaign,
    #     resources={"tiger3": resource},
    #     policy="time",
    #     target_resource="tiger3",
    # )

    # b.run()
