"""Tests for socm.core.models module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from numbers import Number


# Mock pydantic BaseModel for testing
class MockBaseModel:
    model_fields = {}
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.__dict__.update(kwargs)


# Mock pydantic field info
class MockFieldInfo:
    def __init__(self, annotation):
        self.annotation = annotation


def test_imports():
    """Test that imports work correctly."""
    # These should not raise import errors when mocked properly
    with patch('socm.core.models.BaseModel', MockBaseModel):
        with patch('socm.core.models.TaskDescription', Mock):
            from socm.core.models import Resource, Workflow, Campaign


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_resource_creation():
    """Test Resource model creation."""
    from socm.core.models import Resource
    
    resource = Resource(
        name="test_resource",
        nodes=4,
        cores_per_node=112,
        memory_per_node=64000,
        default_queue="normal",
        maximum_walltime=1440
    )
    
    assert resource.name == "test_resource"
    assert resource.nodes == 4
    assert resource.cores_per_node == 112
    assert resource.memory_per_node == 64000
    assert resource.default_queue == "normal"
    assert resource.maximum_walltime == 1440


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_creation():
    """Test Workflow model creation."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test_workflow",
        executable="test_exe",
        context="test_context",
        subcommand="test_sub",
        id=1,
        environment={"ENV_VAR": "value"},
        resources={"ranks": 8, "threads": 4}
    )
    
    assert workflow.name == "test_workflow"
    assert workflow.executable == "test_exe"
    assert workflow.context == "test_context"
    assert workflow.subcommand == "test_sub"
    assert workflow.id == 1
    assert workflow.environment == {"ENV_VAR": "value"}
    assert workflow.resources == {"ranks": 8, "threads": 4}


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_abstract_methods():
    """Test that abstract methods raise NotImplementedError."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test",
        executable="exe",
        context="ctx",
        subcommand="sub"
    )
    
    with pytest.raises(NotImplementedError):
        workflow.get_command()
    
    with pytest.raises(NotImplementedError):
        workflow.get_arguments()
    
    with pytest.raises(NotImplementedError):
        workflow.get_tasks()


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_get_numeric_fields():
    """Test get_numeric_fields method."""
    from socm.core.models import Workflow
    
    # Create a workflow with mixed field types
    workflow = Workflow(
        name="test",
        executable="exe", 
        context="ctx",
        subcommand="sub",
        id=123,  # numeric
        numeric_field=456  # numeric
    )
    
    # Add some additional numeric attributes
    workflow.float_field = 3.14
    workflow.list_of_numbers = [1, 2, 3]
    workflow.string_field = "not_numeric"
    
    avoid_attributes = ["name", "executable", "context", "subcommand"]
    numeric_fields = workflow.get_numeric_fields(avoid_attributes)
    
    # Should include numeric fields but avoid specified attributes
    assert "name" not in numeric_fields
    assert "executable" not in numeric_fields
    assert "context" not in numeric_fields
    assert "subcommand" not in numeric_fields
    assert "string_field" not in numeric_fields


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_get_numeric_fields_with_none_values():
    """Test get_numeric_fields handles None values correctly."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test",
        executable="exe",
        context="ctx", 
        subcommand="sub",
        id=None,  # None value should be skipped
        environment=None  # None value should be skipped
    )
    
    numeric_fields = workflow.get_numeric_fields()
    
    # None values should not be included
    assert "id" not in numeric_fields
    assert "environment" not in numeric_fields


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_get_categorical_fields():
    """Test get_categorical_fields method."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test",
        executable="exe",
        context="ctx",
        subcommand="sub"
    )
    
    # Add some additional string attributes
    workflow.string_field = "categorical"
    workflow.numeric_field = 123
    workflow.list_of_strings = ["a", "b", "c"]
    
    avoid_attributes = ["context", "subcommand"]
    categorical_fields = workflow.get_categorical_fields(avoid_attributes)
    
    # Should include string fields but avoid specified attributes
    assert "context" not in categorical_fields
    assert "subcommand" not in categorical_fields
    assert "numeric_field" not in categorical_fields


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_get_categorical_fields_with_none_values():
    """Test get_categorical_fields handles None values correctly."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test",
        executable="exe",
        context="ctx",
        subcommand="sub",
        environment=None  # None value should be skipped
    )
    
    categorical_fields = workflow.get_categorical_fields()
    
    # None values should not be included
    assert "environment" not in categorical_fields


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_campaign_creation():
    """Test Campaign model creation."""
    from socm.core.models import Campaign, Workflow
    
    workflow1 = Workflow(name="w1", executable="exe1", context="ctx1")
    workflow2 = Workflow(name="w2", executable="exe2", context="ctx2")
    
    campaign = Campaign(
        id=1,
        workflows=[workflow1, workflow2],
        deadline="2d",
        resource="tiger3"
    )
    
    assert campaign.id == 1
    assert len(campaign.workflows) == 2
    assert campaign.deadline == "2d"
    assert campaign.resource == "tiger3"


@patch('socm.core.models.BaseModel', MockBaseModel)
@patch('socm.core.models.TaskDescription', Mock)
def test_workflow_extra_attributes():
    """Test that Workflow allows extra attributes due to model_config."""
    from socm.core.models import Workflow
    
    workflow = Workflow(
        name="test",
        executable="exe",
        context="ctx",
        extra_field="extra_value",  # This should be allowed
        another_extra=123
    )
    
    assert workflow.extra_field == "extra_value"
    assert workflow.another_extra == 123