"""Tests for socm.__main__ module entry point functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from argparse import ArgumentParser


@patch('socm.__main__.toml')
@patch('socm.__main__.get_workflow_entries')
@patch('socm.__main__.registered_workflows')
@patch('socm.__main__.subcampaign_map')
@patch('socm.__main__.Campaign')
@patch('socm.__main__.Resource')
@patch('socm.__main__.Bookkeeper')
def test_get_parser():
    """Test get_parser function returns proper ArgumentParser."""
    from socm.__main__ import get_parser
    
    parser = get_parser()
    
    assert isinstance(parser, ArgumentParser)
    assert parser.description == "Run the SO campaign."


@patch('socm.__main__.toml')
@patch('socm.__main__.get_workflow_entries')
@patch('socm.__main__.registered_workflows')
@patch('socm.__main__.subcampaign_map')
@patch('socm.__main__.Campaign')
@patch('socm.__main__.Resource')
@patch('socm.__main__.Bookkeeper')
def test_get_parser_arguments():
    """Test that get_parser configures required arguments."""
    from socm.__main__ import get_parser
    
    parser = get_parser()
    
    # Check that --toml/-t argument is configured
    actions = parser._actions
    toml_action = None
    for action in actions:
        if '--toml' in action.option_strings:
            toml_action = action
            break
    
    assert toml_action is not None
    assert '-t' in toml_action.option_strings
    assert '--toml' in toml_action.option_strings
    assert toml_action.required is True
    assert toml_action.type == str


@patch('socm.__main__.toml')
@patch('socm.__main__.get_workflow_entries') 
@patch('socm.__main__.registered_workflows')
@patch('socm.__main__.subcampaign_map')
@patch('socm.__main__.Campaign')
@patch('socm.__main__.Resource')
@patch('socm.__main__.Bookkeeper')
def test_main_argument_parsing(mock_bookkeeper, mock_resource, mock_campaign, 
                              mock_subcampaign_map, mock_registered_workflows,
                              mock_get_workflow_entries, mock_toml):
    """Test main function argument parsing and workflow loading."""
    from socm.__main__ import main
    
    # Mock the configuration
    test_config = {
        "campaign": {
            "deadline": "2d",
            "resources": {"nodes": 4, "cores-per-node": 112},
            "ml-mapmaking": {
                "context": "context.yaml",
                "area": "area.fits",
                "output_dir": "output"
            }
        }
    }
    
    mock_toml.load.return_value = test_config
    mock_get_workflow_entries.return_value = {
        "ml-mapmaking": {
            "context": "context.yaml",
            "area": "area.fits", 
            "output_dir": "output"
        }
    }
    
    # Mock workflow factory
    mock_workflow = Mock()
    mock_workflow.id = None
    mock_workflow_factory = Mock()
    mock_workflow_factory.get_workflows.return_value = [mock_workflow]
    mock_registered_workflows.__getitem__.return_value = mock_workflow_factory
    mock_registered_workflows.__contains__.return_value = True
    
    # Mock the resource and campaign creation
    mock_resource_instance = Mock()
    mock_resource.return_value = mock_resource_instance
    mock_campaign_instance = Mock()
    mock_campaign.return_value = mock_campaign_instance
    
    # Mock bookkeeper
    mock_bookkeeper_instance = Mock()
    mock_bookkeeper.return_value = mock_bookkeeper_instance
    
    # Mock sys.argv
    with patch('sys.argv', ['socm', '--toml', 'test.toml']):
        main()
    
    # Verify the configuration was loaded
    mock_toml.load.assert_called_once_with('test.toml')
    mock_get_workflow_entries.assert_called_once()
    
    # Verify workflow factory was called
    mock_workflow_factory.get_workflows.assert_called_once()
    
    # Verify workflow got assigned an ID
    assert mock_workflow.id == 1
    
    # Verify Campaign was created with correct parameters
    mock_campaign.assert_called_once()
    call_args = mock_campaign.call_args
    assert call_args[1]['id'] == 1
    assert call_args[1]['deadline'] == "2d"
    assert len(call_args[1]['workflows']) == 1
    
    # Verify Resource was created with correct parameters
    mock_resource.assert_called_once()
    call_args = mock_resource.call_args
    assert call_args[1]['name'] == "tiger3"
    assert call_args[1]['nodes'] == 4
    assert call_args[1]['cores_per_node'] == 112
    
    # Verify Bookkeeper was created and run
    mock_bookkeeper.assert_called_once()
    mock_bookkeeper_instance.run.assert_called_once()


@patch('socm.__main__.toml')
@patch('socm.__main__.get_workflow_entries')
@patch('socm.__main__.registered_workflows')
@patch('socm.__main__.subcampaign_map')
@patch('socm.__main__.Campaign')
@patch('socm.__main__.Resource')
@patch('socm.__main__.Bookkeeper')
def test_main_multiple_workflows(mock_bookkeeper, mock_resource, mock_campaign,
                                mock_subcampaign_map, mock_registered_workflows,
                                mock_get_workflow_entries, mock_toml):
    """Test main function with multiple workflows."""
    from socm.__main__ import main
    
    # Mock configuration with multiple workflows
    test_config = {
        "campaign": {
            "deadline": "1d",
            "resources": {"nodes": 2, "cores-per-node": 56}
        }
    }
    
    mock_toml.load.return_value = test_config
    mock_get_workflow_entries.return_value = {
        "workflow1": {"param": "value1"},
        "workflow2": {"param": "value2"}
    }
    
    # Mock workflow factories returning multiple workflows
    mock_workflow1 = Mock()
    mock_workflow1.id = None
    mock_workflow2 = Mock() 
    mock_workflow2.id = None
    mock_workflow3 = Mock()
    mock_workflow3.id = None
    
    mock_workflow_factory = Mock()
    mock_workflow_factory.get_workflows.side_effect = [
        [mock_workflow1, mock_workflow2],  # First factory returns 2 workflows
        [mock_workflow3]  # Second factory returns 1 workflow
    ]
    
    mock_registered_workflows.__getitem__.return_value = mock_workflow_factory
    mock_registered_workflows.__contains__.return_value = True
    
    # Mock other components
    mock_resource.return_value = Mock()
    mock_campaign.return_value = Mock()
    mock_bookkeeper_instance = Mock()
    mock_bookkeeper.return_value = mock_bookkeeper_instance
    
    with patch('sys.argv', ['socm', '--toml', 'test.toml']):
        main()
    
    # Verify workflow IDs are assigned sequentially
    assert mock_workflow1.id == 1
    assert mock_workflow2.id == 2
    assert mock_workflow3.id == 3
    
    # Verify Campaign was called with all 3 workflows
    call_args = mock_campaign.call_args
    assert len(call_args[1]['workflows']) == 3


@patch('socm.__main__.toml')
@patch('socm.__main__.get_workflow_entries')
@patch('socm.__main__.registered_workflows')
@patch('socm.__main__.subcampaign_map') 
@patch('socm.__main__.Campaign')
@patch('socm.__main__.Resource')
@patch('socm.__main__.Bookkeeper')
def test_main_unregistered_workflow(mock_bookkeeper, mock_resource, mock_campaign,
                                   mock_subcampaign_map, mock_registered_workflows,
                                   mock_get_workflow_entries, mock_toml):
    """Test main function skips unregistered workflow types."""
    from socm.__main__ import main
    
    test_config = {
        "campaign": {
            "deadline": "2d",
            "resources": {"nodes": 4, "cores-per-node": 112}
        }
    }
    
    mock_toml.load.return_value = test_config
    mock_get_workflow_entries.return_value = {
        "registered-workflow": {"param": "value1"},
        "unregistered-workflow": {"param": "value2"}
    }
    
    # Mock registered_workflows to only contain first workflow
    def mock_contains(key):
        return key == "registered-workflow"
    
    mock_registered_workflows.__contains__.side_effect = mock_contains
    
    mock_workflow = Mock()
    mock_workflow.id = None
    mock_workflow_factory = Mock()
    mock_workflow_factory.get_workflows.return_value = [mock_workflow]
    mock_registered_workflows.__getitem__.return_value = mock_workflow_factory
    
    # Mock other components
    mock_resource.return_value = Mock()
    mock_campaign.return_value = Mock()
    mock_bookkeeper_instance = Mock()
    mock_bookkeeper.return_value = mock_bookkeeper_instance
    
    with patch('sys.argv', ['socm', '--toml', 'test.toml']):
        main()
    
    # Verify only the registered workflow was processed
    mock_workflow_factory.get_workflows.assert_called_once_with({"param": "value1"})
    
    # Verify Campaign was called with only 1 workflow
    call_args = mock_campaign.call_args
    assert len(call_args[1]['workflows']) == 1