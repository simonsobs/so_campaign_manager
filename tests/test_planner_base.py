"""Tests for socm.planner.base module using mocks."""

from unittest.mock import Mock, patch

import pytest


@patch("socm.planner.base.ru")
@patch("socm.planner.base.os")
def test_planner_initialization(
    mock_os, mock_ru):
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
def test_planner_initialization_with_none_values(mock_os, mock_ru):
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
def test_planner_plan_not_implemented(mock_os, mock_ru):
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
def test_planner_replan_not_implemented(mock_os, mock_ru):
    """Test that plan method raises NotImplementedError."""
    mock_ru.generate_id.return_value = "planner.0003"
    mock_ru.Logger.return_value = Mock()
    mock_ru.ID_CUSTOM = "custom"
    mock_os.getcwd.return_value = "/test/path"

    from socm.planner.base import Planner

    planner = Planner()

    with pytest.raises(NotImplementedError, match="Replan method is not implemented"):
        planner.replan()
