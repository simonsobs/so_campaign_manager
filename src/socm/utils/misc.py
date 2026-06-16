import ast
from typing import Dict, List

import networkx as nx


def parse_comma_separated_fields(config: dict, fields_to_parse: List[str]) -> dict:
    """
    Convert comma-separated string values in a config dict to Python lists.

    Recursively traverses nested dicts. For each key found in
    ``fields_to_parse`` whose value is a comma-separated string, the string is
    split on commas and each token is evaluated with :func:`ast.literal_eval`.

    Parameters
    ----------
    config : dict
        The configuration dictionary to process in-place.
    fields_to_parse : list of str
        Keys whose values should be converted from comma-separated strings to
        lists.

    Returns
    -------
    dict
        The mutated ``config`` dictionary (modified in-place and returned for
        convenience).
    """
    for key, value in config.items():
        if isinstance(value, dict):
            parse_comma_separated_fields(value, fields_to_parse)
        elif key in fields_to_parse and isinstance(value, str) and ',' in value:
            config[key] = [ast.literal_eval(item.strip()) for item in value.split(',')]
    return config


def get_workflow_entries(campaign_dict: dict, subcampaign_map: Dict[str, list] | None = None) -> Dict[str, dict]:
    """
    Extract workflow entries from a campaign dictionary using a subcampaign mapping.

    Iterates over the top-level keys inside ``campaign_dict["campaign"]`` and
    produces a flat dictionary of workflow configurations. Keys that appear in
    ``subcampaign_map`` are treated as subcampaigns: their workflow-specific
    sub-sections are merged with the subcampaign's common configuration and
    re-keyed as ``"<subcampaign>.<workflow>"``.

    Parameters
    ----------
    campaign_dict : dict
        A dictionary containing the full campaign configuration, expected to have
        a top-level ``"campaign"`` key whose value is the campaign section.
    subcampaign_map : dict of str to list of str, or None, optional
        A mapping of subcampaign names to the list of workflow names they contain.
        For example: ``{"ml-null-tests": ["mission-tests", "wafer-tests"]}``.
        When ``None``, no subcampaign expansion is performed.

    Returns
    -------
    dict of str to dict
        A flat mapping of workflow keys to their merged configuration
        dictionaries. Direct (non-subcampaign) workflows are keyed by their
        original name; subcampaign workflows are keyed as
        ``"<subcampaign>.<workflow>"``.
    """
    campaign_data = campaign_dict.get("campaign", {})

    # Default empty map if none provided
    if subcampaign_map is None:
        subcampaign_map = {}

    # Collect all workflows (direct and from subcampaigns)
    workflows = {}

    for workflow_key, workflow_value in campaign_data.items():
        # Skip non-dictionary values
        if not isinstance(workflow_value, dict):
            continue

        # Check if this is a known subcampaign
        if workflow_key in subcampaign_map:
            # Process known workflows for this subcampaign
            subcampaign_name = workflow_key
            subcampaign_workflows = subcampaign_map[workflow_key]

            # Create a copy of the subcampaign config without its workflows
            subcampaign_common_config = {
                k: v for k, v in workflow_value.items() if k not in subcampaign_workflows
            }

            for workflow_name in subcampaign_workflows:
                if workflow_name in workflow_value:
                    # Start with the workflow's own config
                    workflow_config = workflow_value[workflow_name].copy()

                    # Update with common subcampaign config
                    workflow_config.update(subcampaign_common_config)

                    if isinstance(workflow_config, dict):
                        # Create combined key: subcampaign.workflow_name
                        workflows[f"{subcampaign_name}.{workflow_name}"] = (
                            workflow_config
                        )
        else:
            # Treat as regular workflow
            workflows[workflow_key] = workflow_value

    return workflows


def get_query_from_file(file_path: str) -> str:
    """
    Build an ``obs_id IN (...)`` query string from a file of observation IDs.

    Reads a plain-text file containing one observation ID per line and
    constructs an SQL-style ``IN`` clause suitable for use with sotodlib's
    ``obsdb.query()``.

    Parameters
    ----------
    file_path : str
        Path to a text file with one observation ID per line. Blank lines and
        trailing whitespace are stripped.

    Returns
    -------
    str
        A query string of the form ``obs_id IN ('id1','id2',...)``.
    """
    query = "obs_id IN ("
    with open(file_path, "r") as file:
        obslist = file.readlines()
        for obs_id in obslist:
            obs_id = obs_id.strip()
            query += f"'{obs_id}',"
    query = query.rstrip(",")
    query += ")"

    return query


def print_plan(graph: nx.DiGraph) -> None:
    """
    Render and save the execution plan dependency graph as a PNG image.

    Uses ``graphviz_layout`` to produce a hierarchical (top-down) layout
    and saves the result to ``graph.png`` in the current working directory.

    Parameters
    ----------
    graph : networkx.DiGraph
        The plan dependency graph to visualise.

    Notes
    -----
    Requires ``matplotlib`` and the ``pydot`` / ``graphviz`` packages to be
    installed. The output file is always named ``graph.png`` and is written
    to the current working directory.
    """
    import matplotlib.pyplot as plt
    from networkx.drawing.nx_pydot import graphviz_layout

    pos = graphviz_layout(graph, prog='dot')
    plt.figure(figsize=(12, 8))
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', arrows=True, node_size=500)
    plt.savefig("graph.png", dpi=300, bbox_inches='tight')
