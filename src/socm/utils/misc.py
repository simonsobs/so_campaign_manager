from typing import Dict


def get_workflow_entries(campaign_dict: dict, subcampaign_map: Dict[str, list] | None = None) -> Dict[str, dict]:
    """
    Extract workflow entries from a campaign dictionary using a predefined mapping.

    Args:
        campaign_dict: A dictionary containing campaign configuration
        subcampaign_map: A dictionary mapping subcampaign names to lists of their workflow names
                         E.g., {"ml-null-test": ["mission-tests", "wafer-tests"]}

    Returns:
        Dictionary containing workflow entries
    """
    campaign_data = campaign_dict.get("campaign", {})

    # Default empty map if none provided
    if subcampaign_map is None:
        subcampaign_map = {}

    # Collect all workflows (direct and from subcampaigns)
    workflows = {}

    for key, value in campaign_data.items():
        # Skip non-dictionary values
        if not isinstance(value, dict):
            continue

        # Check if this is a known subcampaign
        if key in subcampaign_map:
            # Process known workflows for this subcampaign
            subcampaign_name = key
            subcampaign_workflows = subcampaign_map[key]

            # Create a copy of the subcampaign config without its workflows
            subcampaign_common_config = {
                k: v for k, v in value.items() if k not in subcampaign_workflows
            }

            for workflow_name in subcampaign_workflows:
                if workflow_name in value:
                    # Start with the workflow's own config
                    workflow_config = value[workflow_name].copy()

                    # Update with common subcampaign config
                    workflow_config.update(subcampaign_common_config)

                    if isinstance(workflow_config, dict):
                        # Create combined key: subcampaign.workflow_name
                        workflows[f"{subcampaign_name}.{workflow_name}"] = (
                            workflow_config
                        )
        else:
            # Treat as regular workflow
            workflows[key] = value

    return workflows


def get_query_from_file(file_path: str) -> str:
    """
    Extract a SQL query from a file.

    Args:
        file_path: The path to the file containing the SQL query.

    Returns:
        The SQL query as a string.
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
