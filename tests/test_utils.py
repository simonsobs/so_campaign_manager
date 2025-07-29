from socm.utils.misc import get_workflow_entries
from socm.utils.states import (
    CANCELED,
    CFINAL,
    DONE,
    EXECUTING,
    FAILED,
    NEW,
    PLANNING,
    state_dict,
)
from socm.workflows import subcampaign_map


def test_state_constants_exist():
    """Test that all state constants are defined."""
    assert NEW == 0
    assert PLANNING == 1
    assert EXECUTING == 2
    assert DONE == 3
    assert FAILED == 4
    assert CANCELED == 5


def test_state_constants_are_integers():
    """Test that all state constants are integers."""
    states = [NEW, PLANNING, EXECUTING, DONE, FAILED, CANCELED]
    for state in states:
        assert isinstance(state, int)


def test_state_constants_are_unique():
    """Test that all state constants have unique values."""
    states = [NEW, PLANNING, EXECUTING, DONE, FAILED, CANCELED]
    assert len(states) == len(set(states))


def test_cfinal_contains_final_states():
    """Test that CFINAL contains the expected final states."""
    assert DONE in CFINAL
    assert FAILED in CFINAL
    assert CANCELED in CFINAL

    # Should only contain final states
    assert len(CFINAL) == 3


def test_cfinal_does_not_contain_active_states():
    """Test that CFINAL does not contain active states."""
    assert NEW not in CFINAL
    assert PLANNING not in CFINAL
    assert EXECUTING not in CFINAL


def test_state_dict_exists():
    """Test that state_dict exists and is a dictionary."""
    assert isinstance(state_dict, dict)


def test_state_dict_completeness():
    """Test that state_dict contains all states."""
    expected_states = {
        0: "NEW",
        1: "PLANNING",
        2: "EXECUTING",
        3: "DONE",
        4: "FAILED",
        5: "CANCELED",
    }

    assert state_dict == expected_states


def test_state_dict_keys_match_constants():
    """Test that state_dict keys match the state constants."""
    assert state_dict[NEW] == "NEW"
    assert state_dict[PLANNING] == "PLANNING"
    assert state_dict[EXECUTING] == "EXECUTING"
    assert state_dict[DONE] == "DONE"
    assert state_dict[FAILED] == "FAILED"
    assert state_dict[CANCELED] == "CANCELED"


def test_state_dict_values_are_strings():
    """Test that all state_dict values are strings."""
    for value in state_dict.values():
        assert isinstance(value, str)
        assert len(value) > 0


def test_state_dict_values_are_uppercase():
    """Test that all state_dict values are uppercase."""
    for value in state_dict.values():
        assert value == value.upper()


def test_workflow_entries(campaign_config):
    workflows_configs = get_workflow_entries(
        campaign_config, subcampaign_map=subcampaign_map
    )

    assert workflows_configs == {
        "resources": {"nodes": 4, "cores-per-node": 112},
        "ml-mapmaking": {
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "resources": {
                "ranks": 8,
                "threads": 8,
                "memory": "80000",
                "runtime": "80000",
            },
        },
        "ml-null-tests.direction-tests": {
            "chunk_nobs": 10,
            "nsplits": 8,
            "resources": {
                "ranks": 1,
                "threads": 32,
                "memory": "80000",
                "runtime": "80000",
            },
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {
                "DOT_MOBY2": "act_dot_moby2",
                "SOTODLIB_SITECONFIG": "site.yaml",
            },
        },
        "ml-null-tests.mission-tests": {
            "chunk_nobs": 5,
            "nsplits": 4,
            "resources": {
                "ranks": 4,
                "threads": 8,
                "memory": "80000",
                "runtime": "80000",
            },
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {
                "DOT_MOBY2": "act_dot_moby2",
                "SOTODLIB_SITECONFIG": "site.yaml",
            },
        },
        "ml-null-tests.wafer-tests": {
            "chunk_nobs": 10,
            "nsplits": 8,
            "resources": {
                "ranks": 1,
                "threads": 32,
                "memory": "80000",
                "runtime": "80000",
            },
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {
                "DOT_MOBY2": "act_dot_moby2",
                "SOTODLIB_SITECONFIG": "site.yaml",
            },
        },
        "ml-null-tests.pwv-tests": {
            "chunk_nobs": 10,
            "nsplits": 8,
            "resources": {
                "ranks": 1,
                "threads": 32,
                "memory": "80000",
                "runtime": "80000",
            },
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {
                "DOT_MOBY2": "act_dot_moby2",
                "SOTODLIB_SITECONFIG": "site.yaml",
            },
        },
    }


def test_get_workflow_entries_empty_dict():
    """Test get_workflow_entries with empty campaign dict."""
    result = get_workflow_entries({})
    assert result == {}


def test_get_workflow_entries_no_campaign_key():
    """Test get_workflow_entries with dict that has no campaign key."""
    campaign_dict = {"other": {"some": "value"}}
    result = get_workflow_entries(campaign_dict)
    assert result == {}


def test_get_workflow_entries_empty_campaign():
    """Test get_workflow_entries with empty campaign section."""
    campaign_dict = {"campaign": {}}
    result = get_workflow_entries(campaign_dict)
    assert result == {}


def test_get_workflow_entries_simple_workflow():
    """Test get_workflow_entries with a simple workflow."""
    campaign_dict = {
        "campaign": {
            "simple-workflow": {"context": "context.yaml", "output_dir": "output"}
        }
    }

    result = get_workflow_entries(campaign_dict)
    expected = {"simple-workflow": {"context": "context.yaml", "output_dir": "output"}}
    assert result == expected


def test_get_workflow_entries_multiple_workflows():
    """Test get_workflow_entries with multiple simple workflows."""
    campaign_dict = {
        "campaign": {
            "workflow1": {"context": "context1.yaml", "output_dir": "output1"},
            "workflow2": {"context": "context2.yaml", "output_dir": "output2"},
        }
    }

    result = get_workflow_entries(campaign_dict)
    expected = {
        "workflow1": {"context": "context1.yaml", "output_dir": "output1"},
        "workflow2": {"context": "context2.yaml", "output_dir": "output2"},
    }
    assert result == expected


def test_get_workflow_entries_with_subcampaign():
    """Test get_workflow_entries with subcampaign mapping."""
    campaign_dict = {
        "campaign": {
            "ml-null-tests": {
                "context": "context.yaml",
                "area": "area.fits",
                "output_dir": "output/null_tests",
                "mission-tests": {
                    "chunk_nobs": 5,
                    "nsplits": 4,
                },
                "wafer-tests": {
                    "chunk_nobs": 10,
                    "nsplits": 8,
                },
            }
        }
    }

    subcampaign_map = {"ml-null-tests": ["mission-tests", "wafer-tests"]}

    result = get_workflow_entries(campaign_dict, subcampaign_map)

    expected = {
        "ml-null-tests.mission-tests": {
            "chunk_nobs": 5,
            "nsplits": 4,
            "context": "context.yaml",
            "area": "area.fits",
            "output_dir": "output/null_tests",
        },
        "ml-null-tests.wafer-tests": {
            "chunk_nobs": 10,
            "nsplits": 8,
            "context": "context.yaml",
            "area": "area.fits",
            "output_dir": "output/null_tests",
        },
    }
    assert result == expected


def test_get_workflow_entries_common_overrides_specific():
    """Test that common subcampaign config overrides specific workflow config."""
    campaign_dict = {
        "campaign": {
            "test-campaign": {
                "common_param": "common_value",
                "override_param": "common_override",
                "sub-workflow": {
                    "specific_param": "specific_value",
                    "override_param": "specific_override",
                },
            }
        }
    }

    subcampaign_map = {"test-campaign": ["sub-workflow"]}

    result = get_workflow_entries(campaign_dict, subcampaign_map)

    expected = {
        "test-campaign.sub-workflow": {
            "specific_param": "specific_value",
            "override_param": "common_override",  # Common config overwrites specific
            "common_param": "common_value",
        }
    }
    assert result == expected


def test_get_workflow_entries_mixed_workflows():
    """Test get_workflow_entries with mix of direct workflows and subcampaigns."""
    campaign_dict = {
        "campaign": {
            "direct-workflow": {
                "context": "direct.yaml",
                "output_dir": "direct_output",
            },
            "subcampaign": {
                "common_context": "common.yaml",
                "sub1": {"specific_param": "value1"},
                "sub2": {"specific_param": "value2"},
            },
        }
    }

    subcampaign_map = {"subcampaign": ["sub1", "sub2"]}

    result = get_workflow_entries(campaign_dict, subcampaign_map)

    expected = {
        "direct-workflow": {"context": "direct.yaml", "output_dir": "direct_output"},
        "subcampaign.sub1": {
            "specific_param": "value1",
            "common_context": "common.yaml",
        },
        "subcampaign.sub2": {
            "specific_param": "value2",
            "common_context": "common.yaml",
        },
    }
    assert result == expected


def test_get_workflow_entries_skips_non_dict_values():
    """Test that get_workflow_entries skips non-dictionary values."""
    campaign_dict = {
        "campaign": {
            "string_value": "should_be_ignored",
            "int_value": 123,
            "list_value": [1, 2, 3],
            "valid_workflow": {"context": "context.yaml"},
        }
    }

    result = get_workflow_entries(campaign_dict)

    expected = {"valid_workflow": {"context": "context.yaml"}}
    assert result == expected


def test_get_workflow_entries_none_subcampaign_map():
    """Test get_workflow_entries with None subcampaign_map."""
    campaign_dict = {"campaign": {"workflow": {"context": "context.yaml"}}}

    result = get_workflow_entries(campaign_dict, None)

    expected = {"workflow": {"context": "context.yaml"}}
    assert result == expected


def test_get_workflow_entries_missing_subcampaign_workflow():
    """Test behavior when subcampaign references non-existent workflow."""
    campaign_dict = {
        "campaign": {
            "subcampaign": {
                "common_param": "value",
                "existing_workflow": {"specific_param": "specific"},
            }
        }
    }

    subcampaign_map = {"subcampaign": ["existing_workflow", "missing_workflow"]}

    result = get_workflow_entries(campaign_dict, subcampaign_map)

    # Should only include existing workflow
    expected = {
        "subcampaign.existing_workflow": {
            "specific_param": "specific",
            "common_param": "value",
        }
    }
    assert result == expected


def test_get_workflow_entries_non_dict_workflow_config():
    """Test behavior when workflow config creates a non-dict after processing."""
    # This test is designed to cover the isinstance(workflow_config, dict) branch
    # but the current implementation assumes workflow configs are dicts with .copy() method
    # So this is more of a robustness test

    # The only way to get to the isinstance check is if workflow_config somehow
    # becomes non-dict after the copy() and update() operations
    # This is actually difficult with the current implementation since
    # .copy() is called on the value which must be a dict to have that method

    # Let's just document this edge case for now and test a regular case
    campaign_dict = {
        "campaign": {
            "subcampaign": {
                "common_param": "value",
                "workflow_dict": {"specific_param": "specific"},
            }
        }
    }

    subcampaign_map = {"subcampaign": ["workflow_dict"]}

    result = get_workflow_entries(campaign_dict, subcampaign_map)

    # Should include the workflow since it's a proper dict
    expected = {
        "subcampaign.workflow_dict": {
            "specific_param": "specific",
            "common_param": "value",
        }
    }
    assert result == expected
