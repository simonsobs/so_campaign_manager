import pytest
from unittest import mock

from socm.workflows.ml_null_tests import DirectionNullTestWorkflow


@pytest.fixture
def direction_config():
    """Configuration for direction null test workflow."""
    return {
        "context": "context.yaml",
        "area": "so_geometry_v20250306_lat_f090.fits",
        "output_dir": "output/direction_tests",
        "bands": "f090",
        "wafer": "ws0",
        "comps": "TQU",
        "maxiter": 10,
        "query": "obs_id IN ('obs1', 'obs2', 'obs3', 'obs4', 'obs5', 'obs6')",
        "tiled": 1,
        "site": "act",
        "chunk_nobs": 3,
        "nsplits": 2,
        "environment": {
            "DOT_MOBY2": "act_dot_moby2",
            "SOTODLIB_SITECONFIG": "site.yaml"
        },
    }


@pytest.fixture
def mock_direction_context():
    """Create a fixture that returns a mock Context class for direction tests."""
    with mock.patch(
        "socm.workflows.ml_null_tests.direction_null_test.Context"
    ) as mocked:
        class MockContextImpl:
            def __init__(self, context_file):
                self.obsdb = mock.Mock()
                # Create mock observations with different scan directions
                self.obsdb.query = mock.Mock(
                    return_value=[
                        {
                            "obs_id": "obs1", 
                            "n_samples": 1000, 
                            "timestamp": 1000000000, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                        {
                            "obs_id": "obs2", 
                            "n_samples": 1000, 
                            "timestamp": 1000000100, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                        {
                            "obs_id": "obs3", 
                            "n_samples": 1000, 
                            "timestamp": 1000000200, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                        {
                            "obs_id": "obs4", 
                            "n_samples": 1000, 
                            "timestamp": 1000000300, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                        {
                            "obs_id": "obs5", 
                            "n_samples": 1000, 
                            "timestamp": 1000000400, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                        {
                            "obs_id": "obs6", 
                            "n_samples": 1000, 
                            "timestamp": 1000000500, 
                            "wafer_slots_list": "ws0", 
                            "tube_slot": "st1"
                        },
                    ]
                )

        mocked.side_effect = MockContextImpl
        yield mocked


def test_direction_workflow_initialization(mock_direction_context, direction_config):
    """Test that DirectionNullTestWorkflow initializes correctly."""
    workflow = DirectionNullTestWorkflow(**direction_config)
    
    assert workflow.name == "direction_null_test_workflow"
    assert workflow.nsplits == 2
    assert workflow.chunk_nobs == 3
    assert workflow.context == "context.yaml"
    assert workflow.area == "so_geometry_v20250306_lat_f090.fits"
    assert workflow.output_dir == "output/direction_tests"


def test_direction_workflow_splits(mock_direction_context, direction_config):
    """Test that the direction workflow creates proper splits."""
    workflow = DirectionNullTestWorkflow(**direction_config)
    
    # Check that splits were created
    assert hasattr(workflow, '_splits')
    assert isinstance(workflow._splits, dict)
    
    # Should have splits for different directions
    for direction, splits in workflow._splits.items():
        assert direction in ['rising', 'setting', 'middle']
        assert isinstance(splits, list)
        # Each direction should have nsplits=2 splits (or fewer if no observations)
        assert len(splits) <= 2


def test_direction_workflow_get_workflows(mock_direction_context, direction_config):
    """Test that get_workflows creates appropriate workflow instances."""
    workflows = DirectionNullTestWorkflow.get_workflows(direction_config)
    
    assert isinstance(workflows, list)
    assert len(workflows) > 0
    
    # Check that output directories follow the naming convention
    output_dirs = [w.output_dir for w in workflows]
    
    # Should have directories with direction_ prefix
    direction_dirs = [d for d in output_dirs if 'direction_' in d]
    assert len(direction_dirs) > 0
    
    # Check naming convention: direction_[rising,setting,middle]_split_N
    for output_dir in direction_dirs:
        parts = output_dir.split('/')[-1].split('_')
        assert parts[0] == "direction"
        assert parts[1] in ["rising", "setting", "middle"]
        assert parts[2] == "split"
        assert parts[3].isdigit()


def test_direction_workflow_query_construction(mock_direction_context, direction_config):
    """Test that queries are constructed correctly for each split."""
    workflows = DirectionNullTestWorkflow.get_workflows(direction_config)
    
    for workflow in workflows:
        assert "obs_id IN (" in workflow.query
        assert workflow.query.endswith(")")
        # Ensure no trailing commas
        assert ",)" not in workflow.query


def test_direction_workflow_scan_direction_detection():
    """Test the scan direction detection logic."""
    workflow = DirectionNullTestWorkflow(
        context="context.yaml",
        area="area.fits", 
        output_dir="output",
        chunk_nobs=1
    )
    
    # Test with different observation metadata
    obs_info1 = {"obs_id": "test_obs_1", "start_time": 1000000000}
    obs_info2 = {"obs_id": "test_obs_2", "start_time": 1000000100}
    obs_info3 = {"obs_id": "test_obs_3", "start_time": 1000000200}
    
    direction1 = workflow._get_scan_direction(obs_info1)
    direction2 = workflow._get_scan_direction(obs_info2)
    direction3 = workflow._get_scan_direction(obs_info3)
    
    # Should return valid directions
    assert direction1 in ["rising", "setting", "middle"]
    assert direction2 in ["rising", "setting", "middle"]
    assert direction3 in ["rising", "setting", "middle"]


def test_direction_workflow_error_handling():
    """Test error handling for invalid configurations."""
    base_config = {
        "context": "context.yaml",
        "area": "area.fits",
        "output_dir": "output",
    }
    
    # Test that both chunk_nobs and chunk_duration cannot be set
    with pytest.raises(
        ValueError, match="Only one of chunk_nobs or duration can be set"
    ):
        workflow = DirectionNullTestWorkflow(
            **base_config,
            chunk_nobs=5,
            chunk_duration=60
        )
        workflow._get_splits(None, {})
    
    # Test that one of chunk_nobs or chunk_duration must be set
    with pytest.raises(ValueError, match="Either chunk_nobs or duration must be set"):
        workflow = DirectionNullTestWorkflow(**base_config)
        workflow._get_splits(None, {})


def test_direction_workflow_arguments_exclusion(
    mock_direction_context, direction_config
):
    """Test that direction-specific arguments are properly excluded from command 
    arguments."""
    workflows = DirectionNullTestWorkflow.get_workflows(direction_config)
    
    for workflow in workflows:
        arguments = workflow.get_arguments()
        arg_string = " ".join(arguments)
        
        # Check that direction-specific attributes are excluded
        assert "chunk_nobs" not in arg_string
        assert "nsplits" not in arg_string
        assert "chunk_duration" not in arg_string