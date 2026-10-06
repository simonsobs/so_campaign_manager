import ast
from pathlib import Path
from typing import Any, Dict, List, Union

import networkx as nx


def parse_comma_separated_fields(config: dict, fields_to_parse: List[str]) -> dict:
    """Convert comma-separated string values to lists."""
    for key, value in config.items():
        if isinstance(value, dict):
            parse_comma_separated_fields(value, fields_to_parse)
        elif key in fields_to_parse and isinstance(value, str) and ',' in value:
            config[key] = [ast.literal_eval(item.strip()) for item in value.split(',')]
    return config

def get_workflow_entries(campaign_dict: dict, subcampaign_map: Dict[str, list] | None = None) -> Dict[str, dict]:
    """
    Extract workflow entries from a campaign dictionary using a predefined mapping.

    Parameters
    ----------
    campaign_dict : dict
        A dictionary containing campaign configuration.
    subcampaign_map : dict or None, optional
        A mapping of subcampaign names to lists of their workflow names.
        E.g., {"ml-null-test": ["mission-tests", "wafer-tests"]}.

    Returns
    -------
    dict
        A dictionary containing workflow entries keyed by workflow name.
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
    Build an observation ID filter query from a file of obs IDs.

    Reads a file containing one observation ID per line and constructs
    an ``obs_id IN (...)`` query string for use with sotodlib's obsdb.

    Parameters
    ----------
    file_path : str
        Path to a text file with one observation ID per line.

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


def read_par_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Read an argparse ``@file`` (par file) into a dict of option name to value.

    Follows argparse's default format: every line is exactly one argument, so
    values may contain spaces (e.g. ``2025-01-01 00:00:00``). Supports
    ``--key=value``, ``--key`` followed by a value line, bare ``--flag``
    (True), ``--op.enable`` / ``--op.disable`` (``op`` -> True/False), blank
    lines, ``#`` comment lines and nested ``@other.par`` includes, resolved
    relative to the including file.

    An option given more than once (e.g. ``--patch``) becomes a list of its
    values in order. Passing every value back on the command line keeps
    argparse semantics: append options get all of them, others the last one.

    Parameters
    ----------
    file_path : str or Path
        Path to the par file.

    Returns
    -------
    dict
        Option names without the leading ``--``. Values are strings (or lists
        of strings for repeated options), except for flags and enable/disable
        options, which are booleans.

    Raises
    ------
    ValueError
        If the file contains a value that does not follow an option.
    """
    file_path = Path(file_path)
    tokens = _read_par_tokens(file_path)

    args: Dict[str, Any] = {}

    def _add(key: str, value: Any) -> None:
        if key not in args:
            args[key] = value
        elif isinstance(args[key], list):
            args[key].append(value)
        else:
            args[key] = [args[key], value]

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("--"):
            raise ValueError(f"{file_path}: value {token!r} does not follow an option")
        key, sep, value = token[2:].partition("=")
        if sep:
            _add(key, value)
        elif key.endswith((".enable", ".disable")):
            op_name, _, state = key.rpartition(".")
            args[op_name] = state == "enable"
        elif i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
            _add(key, tokens[i + 1])
            i += 1
        else:
            args[key] = True
        i += 1

    return args


def _read_par_tokens(file_path: Path) -> List[str]:
    """Return the arguments in a par file, one per line, expanding ``@`` includes."""
    tokens = []
    for line in file_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            tokens.extend(_read_par_tokens(file_path.parent / line[1:]))
        else:
            tokens.append(line)
    return tokens


def print_plan(graph: nx.DiGraph) -> None:
    import matplotlib.pyplot as plt
    from networkx.drawing.nx_pydot import graphviz_layout

    pos = graphviz_layout(graph, prog='dot')
    plt.figure(figsize=(12, 8))
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', arrows=True, node_size=500)
    plt.savefig("graph.png", dpi=300, bbox_inches='tight')
