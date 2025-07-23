"""Tests for socm.planner.base module using mocks."""

from unittest.mock import Mock, patch

import pytest


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_initialization(mock_nx, mock_os, mock_ru):
    """Test Planner class initialization."""
    # Mock the dependencies
    mock_ru.generate_id.return_value = "planner.0001"
    mock_ru.Logger.return_value = Mock()
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    # Mock campaign, resources, etc.
    mock_campaign = Mock()
    mock_resources = Mock()
    mock_resource_requirements = {"1": {"memory": 1000, "time": 100}}

    from socm.planner.base import Planner

    planner = Planner(
        campaign=mock_campaign,
        resources=mock_resources,
        resource_requirements=mock_resource_requirements,
        policy="time",
        sid="test_session",
    )

    # Verify initialization
    assert planner._campaign == mock_campaign
    assert planner._resources == mock_resources
    assert planner._resource_requirements == mock_resource_requirements
    assert planner._policy == "time"
    assert isinstance(planner._plan, list)
    assert len(planner._plan) == 0

    # Verify that utilities were called
    mock_ru.generate_id.assert_called_once()
    mock_ru.Logger.assert_called_once()


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_initialization_with_none_values(mock_nx, mock_os, mock_ru):
    """Test Planner initialization with None values."""
    mock_ru.generate_id.return_value = "planner.0002"
    mock_ru.Logger.return_value = Mock()
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()

    assert planner._campaign is None
    assert planner._resources is None
    assert planner._resource_requirements is None
    assert planner._policy is None
    assert isinstance(planner._plan, list)


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_plan_not_implemented(mock_nx, mock_os, mock_ru):
    """Test that plan method raises NotImplementedError."""
    mock_ru.generate_id.return_value = "planner.0003"
    mock_ru.Logger.return_value = Mock()
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()

    with pytest.raises(NotImplementedError, match="Plan method is not implemented"):
        planner.plan()


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_replan_with_parameters(mock_nx, mock_os, mock_ru):
    """Test replan method with all parameters provided."""
    mock_logger = Mock()
    mock_ru.generate_id.return_value = "planner.0004"
    mock_ru.Logger.return_value = mock_logger
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()

    # Mock the plan method to return a value
    expected_plan = [("workflow1", range(0, 10), 100.0, 0.0)]
    planner.plan = Mock(return_value=expected_plan)

    # Test replan with parameters
    mock_campaign = ["workflow1"]
    mock_resources = range(0, 10)
    mock_resource_requirements = {"1": {"memory": 1000}}

    result = planner.replan(
        campaign=mock_campaign,
        resources=mock_resources,
        resource_requirements=mock_resource_requirements,
        start_time=50,
    )

    # Verify that plan was called with correct parameters
    planner.plan.assert_called_once_with(
        campaign=mock_campaign,
        resources=mock_resources,
        resource_requirements=mock_resource_requirements,
        start_time=50,
    )

    # Verify result
    assert result == expected_plan
    assert planner._plan == expected_plan

    # Verify logger was called for replanning
    mock_logger.debug.assert_called_with("Replanning")


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_replan_without_parameters(mock_nx, mock_os, mock_ru):
    """Test replan method with missing parameters."""
    mock_logger = Mock()
    mock_ru.generate_id.return_value = "planner.0005"
    mock_ru.Logger.return_value = mock_logger
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()
    planner.plan = Mock()

    # Test replan without campaign parameter
    result = planner.replan(resources=range(0, 10), resource_requirements={"1": {"memory": 1000}})

    # Plan should not be called
    planner.plan.assert_not_called()

    # Should log "Nothing to plan for"
    mock_logger.debug.assert_called_with("Nothing to plan for")

    # Should return the current plan (which is empty list by default)
    assert result == []


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_replan_partial_parameters(mock_nx, mock_os, mock_ru):
    """Test replan method with only some parameters provided."""
    mock_logger = Mock()
    mock_ru.generate_id.return_value = "planner.0006"
    mock_ru.Logger.return_value = mock_logger
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()
    planner.plan = Mock()

    # Test replan with only campaign and resources (missing resource_requirements)
    _ = planner.replan(campaign=["workflow1"], resources=range(0, 10))

    # Plan should not be called because resource_requirements is missing
    planner.plan.assert_not_called()

    # Should log "Nothing to plan for"
    mock_logger.debug.assert_called_with("Nothing to plan for")


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
@patch("socm.planner.base.nx")
def test_planner_logger_configuration(mock_nx, mock_os, mock_ru):
    """Test that logger is configured correctly."""
    mock_ru.generate_id.return_value = "planner.0007"
    mock_logger = Mock()
    mock_ru.Logger.return_value = mock_logger
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/cwd"

    from socm.planner.base import Planner

    planner = Planner(sid="test_session_id")

    # Verify logger was configured with correct parameters
    mock_ru.Logger.assert_called_once_with(name="planner.0007", level="DEBUG", path="/test/cwd/test_session_id")

    assert planner._logger == mock_logger
