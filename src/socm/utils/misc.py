from sqlite3 import Cursor
from typing import Dict, Tuple
from uuid import uuid4


def generate_ids(namespace: str) -> str:
    return namespace + uuid4().hex[:8]


def dict_factory(cursor: Cursor, row: Tuple) -> Dict:
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def linear_func(x: float, a: float, b: float) -> float:
    return a * x + b


def get_workflow_entries(campaign_dict, subcampaign_map=None):
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
            subcampaign_common_config = {k: v for k, v in value.items() 
                                        if k not in subcampaign_workflows}
            
            for workflow_name in subcampaign_workflows:
                if workflow_name in value:
                    # Start with the workflow's own config
                    workflow_config = value[workflow_name].copy()
                    
                    # Update with common subcampaign config
                    workflow_config.update(subcampaign_common_config)
                    
                    if isinstance(workflow_config, dict):
                        # Create combined key: subcampaign.workflow_name
                        workflows[f"{subcampaign_name}.{workflow_name}"] = workflow_config
        else:
            # Treat as regular workflow
            workflows[key] = value

    return workflows
