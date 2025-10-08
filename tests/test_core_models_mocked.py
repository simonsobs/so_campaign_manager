"""Tests for socm.core.models module with comprehensive mocking."""

import sys
from unittest.mock import Mock

import pytest


class MockBaseModel:
    """Mock pydantic BaseModel for testing."""

    model_fields = {}

    def __init__(self, **kwargs):
        # Set attributes from kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)
        # Ensure all fields are set
        self.__dict__.update(kwargs)


class MockFieldInfo:
    """Mock pydantic FieldInfo."""

    def __init__(self, annotation=None, default=None):
        self.annotation = annotation
        self.default = default


class MockTaskDescription:
    """Mock radical.pilot TaskDescription."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create module-level mocks
mock_modules = {
    "pydantic": Mock(),
    "radical": Mock(),
    "radical.pilot": Mock(),
}

# Set up mock attributes
mock_modules["pydantic"].BaseModel = MockBaseModel
mock_modules["radical.pilot"].TaskDescription = MockTaskDescription

# Add mocks to sys.modules before importing
for module_name, mock_module in mock_modules.items():
    sys.modules[module_name] = mock_module

def test_workflow_creation():
    """Test Workflow model creation."""
    from socm.core.models import Workflow

    workflow = Workflow(
        name="test_workflow",
        executable="/usr/bin/test",
        context="/path/to/context.yaml",
        subcommand="process",
        id=42,
        environment={"PATH": "/usr/bin", "HOME": "/home/user"},
        resources={"cpu": 4, "memory": 8, "time": 2},
    )

    assert workflow.name == "test_workflow"
    assert workflow.executable == "/usr/bin/test"
    assert workflow.context == "/path/to/context.yaml"
    assert workflow.subcommand == "process"
    assert workflow.id == 42
    assert workflow.environment == {"PATH": "/usr/bin", "HOME": "/home/user"}
    assert workflow.resources == {"cpu": 4, "memory": 8, "time": 2}


def test_workflow_defaults():
    """Test Workflow model with default values."""
    from socm.core.models import Workflow

    workflow = Workflow(name="minimal_workflow", executable="echo", context="context.yaml")

    assert workflow.name == "minimal_workflow"
    assert workflow.executable == "echo"
    assert workflow.context == "context.yaml"
    assert workflow.subcommand == ""  # default value
    assert workflow.id is None  # default value
    assert workflow.environment is None  # default value
    assert workflow.resources is None  # default value


def test_workflow_abstract_methods():
    """Test that abstract methods raise NotImplementedError."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test")

    with pytest.raises(NotImplementedError, match="This method should be implemented in subclasses"):
        workflow.get_command()

    with pytest.raises(NotImplementedError, match="This method should be implemented in subclasses"):
        workflow.get_arguments()

    with pytest.raises(NotImplementedError, match="This method should be implemented in subclasses"):
        workflow.get_tasks()


@pytest.mark.skip
def test_workflow_get_numeric_fields_basic():
    """Test get_numeric_fields with basic numeric types."""
    from socm.core.models import Workflow

    workflow = Workflow(
        name="test",
        executable="test",
        context="test",
        id=123,
        cpu_count=8,
        memory_mb=1024,
        timeout_seconds=3600.5,
        string_field="not_numeric",
        list_field=[1, 2, 3],
    )

    # Add additional numeric attributes

    numeric_fields = workflow.get_numeric_fields(avoid_attributes=["name", "executable", "context"])

    # Should include numeric instance attributes
    assert "cpu_count" in numeric_fields
    assert "memory_mb" in numeric_fields
    assert "timeout_seconds" in numeric_fields

    # Should not include non-numeric fields
    assert "string_field" not in numeric_fields
    assert "name" not in numeric_fields
    assert "executable" not in numeric_fields
    assert "context" not in numeric_fields


@pytest.mark.skip
def test_workflow_get_numeric_fields_with_none():
    """Test get_numeric_fields handles None values."""
    from socm.core.models import Workflow

    workflow = Workflow(
        name="test",
        executable="test",
        context="test",
        id=None,  # None value
        environment=None,  # None value
    )

    workflow.valid_number = 42
    workflow.none_value = None

    numeric_fields = workflow.get_numeric_fields()

    # Should include valid numbers
    assert "valid_number" in numeric_fields

    # Should not include None values
    assert "id" not in numeric_fields
    assert "environment" not in numeric_fields
    assert "none_value" not in numeric_fields


@pytest.mark.skip
def test_workflow_get_numeric_fields_list_of_numbers():
    """Test get_numeric_fields with list of numbers."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test")

    workflow.numeric_list = [1, 2, 3, 4]
    workflow.mixed_list = [1, "string", 3]
    workflow.string_list = ["a", "b", "c"]
    workflow.empty_list = []

    numeric_fields = workflow.get_numeric_fields()

    # Should include list of all numbers
    assert "numeric_list" in numeric_fields

    # Should not include mixed or string lists
    assert "mixed_list" not in numeric_fields
    assert "string_list" not in numeric_fields

    # Empty list handling may vary - check if it's included or not


@pytest.mark.skip
def test_workflow_get_categorical_fields_basic():
    """Test get_categorical_fields with basic string types."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test_workflow", executable="test_exe", context="test_context")

    workflow.string_field = "category_value"
    workflow.numeric_field = 123
    workflow.status = "active"

    categorical_fields = workflow.get_categorical_fields(avoid_attributes=["context"])

    # Should include string fields
    assert "name" in categorical_fields
    assert "executable" in categorical_fields
    assert "string_field" in categorical_fields
    assert "status" in categorical_fields

    # Should not include numeric fields
    assert "numeric_field" not in categorical_fields

    # Should not include avoided attributes
    assert "context" not in categorical_fields


@pytest.mark.skip
def test_workflow_get_categorical_fields_with_none():
    """Test get_categorical_fields handles None values."""
    from socm.core.models import Workflow

    workflow = Workflow(
        name="test",
        executable="test",
        context="test",
        subcommand=None,  # None value
    )

    workflow.valid_string = "valid"
    workflow.none_value = None

    categorical_fields = workflow.get_categorical_fields()

    # Should include valid strings
    assert "name" in categorical_fields
    assert "executable" in categorical_fields
    assert "context" in categorical_fields
    assert "valid_string" in categorical_fields

    # Should not include None values
    assert "subcommand" not in categorical_fields
    assert "none_value" not in categorical_fields


@pytest.mark.skip
def test_workflow_get_categorical_fields_list_of_strings():
    """Test get_categorical_fields with list of strings."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test")

    workflow.string_list = ["option1", "option2", "option3"]
    workflow.mixed_list = ["string", 123, "another"]
    workflow.numeric_list = [1, 2, 3]

    categorical_fields = workflow.get_categorical_fields()

    # Should include list of all strings
    assert "string_list" in categorical_fields

    # Should not include mixed or numeric lists
    assert "mixed_list" not in categorical_fields
    assert "numeric_list" not in categorical_fields


def test_campaign_creation():
    """Test Campaign model creation."""
    from socm.core.models import Campaign, Workflow

    workflow1 = Workflow(name="wf1", executable="exe1", context="ctx1", id=1)
    workflow2 = Workflow(name="wf2", executable="exe2", context="ctx2", id=2)

    campaign = Campaign(id=100, workflows=[workflow1, workflow2], deadline="24h", resource="cluster_name")

    assert campaign.id == 100
    assert len(campaign.workflows) == 2
    assert campaign.workflows[0].name == "wf1"
    assert campaign.workflows[1].name == "wf2"
    assert campaign.deadline == "24h"
    assert campaign.resource == "cluster_name"


def test_campaign_default_resource():
    """Test Campaign model with default resource."""
    from socm.core.models import Campaign, Workflow

    workflow = Workflow(name="wf", executable="exe", context="ctx")

    campaign = Campaign(id=200, workflows=[workflow], deadline="12h")

    assert campaign.id == 200
    assert len(campaign.workflows) == 1
    assert campaign.deadline == "12h"
    assert campaign.resource == "tiger3"  # default value


def test_workflow_extra_attributes():
    """Test that Workflow model allows extra attributes."""
    from socm.core.models import Workflow

    # The model should allow extra attributes due to model_config
    workflow = Workflow(
        name="test",
        executable="test",
        context="test",
        custom_field="custom_value",
        another_extra=999,
        complex_extra={"nested": "data"},
    )

    assert workflow.custom_field == "custom_value"
    assert workflow.another_extra == 999
    assert workflow.complex_extra == {"nested": "data"}


@pytest.mark.skip
def test_workflow_get_numeric_fields_edge_cases():
    """Test get_numeric_fields with edge cases."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test")

    # Test with various edge cases
    workflow.zero_value = 0
    workflow.negative_value = -42
    workflow.float_value = 3.14159
    workflow.bool_value = True  # bool is subclass of int in Python
    workflow.complex_value = 3 + 4j

    numeric_fields = workflow.get_numeric_fields()

    assert "zero_value" in numeric_fields
    assert "negative_value" in numeric_fields
    assert "float_value" in numeric_fields

    # Note: complex numbers and booleans may or may not be included
    # depending on the exact implementation of Number checking


def test_workflow_get_numeric_fields_with_model_fields():
    """Test get_numeric_fields using model_fields annotation checking."""
    from typing import List, Optional, Union

    from socm.core.models import Workflow

    # Create a mock field info for testing annotation checking
    class MockFieldInfo:
        def __init__(self, annotation):
            self.annotation = annotation

    # Set up model_fields to test annotation-based detection
    workflow = Workflow(name="test", executable="test", context="test")

    # Mock the model_fields to test annotation checking paths
    workflow.__class__.model_fields = {
        "id": MockFieldInfo(Optional[int]),
        "count": MockFieldInfo(int),
        "rate": MockFieldInfo(float),
        "name": MockFieldInfo(str),
        "tags": MockFieldInfo(List[str]),
        "scores": MockFieldInfo(List[int]),
        "mixed_union": MockFieldInfo(Union[str, int]),
        "numeric_union": MockFieldInfo(Union[int, float]),
    }

    # Set some actual values
    workflow.id = 123
    workflow.count = 456
    workflow.rate = 3.14
    workflow.name = "test_name"
    workflow.tags = ["tag1", "tag2"]
    workflow.scores = [10, 20, 30]
    workflow.mixed_union = "string_value"
    workflow.numeric_union = 42

    numeric_fields = workflow.get_numeric_fields()

    # Should detect fields based on annotations
    assert "id" in numeric_fields  # Optional[int]
    assert "count" in numeric_fields  # int
    assert "rate" in numeric_fields  # float
    assert "scores" in numeric_fields  # List[int]
    assert "numeric_union" in numeric_fields  # Union[int, float]

    # Should not detect non-numeric fields
    assert "name" not in numeric_fields  # str
    assert "tags" not in numeric_fields  # List[str]

    # Clean up
    workflow.__class__.model_fields = {}


def test_workflow_get_categorical_fields_with_model_fields():
    """Test get_categorical_fields using model_fields annotation checking."""
    from typing import List, Optional, Union

    from socm.core.models import Workflow

    class MockFieldInfo:
        def __init__(self, annotation):
            self.annotation = annotation

    workflow = Workflow(name="test", executable="test", context="test")

    # Mock the model_fields to test annotation checking paths
    workflow.__class__.model_fields = {
        "name": MockFieldInfo(str),
        "status": MockFieldInfo(Optional[str]),
        "tags": MockFieldInfo(List[str]),
        "count": MockFieldInfo(int),
        "numbers": MockFieldInfo(List[int]),
        "mixed_union": MockFieldInfo(Union[str, int]),
        "string_union": MockFieldInfo(Union[str, bool]),
    }

    # Set actual values
    workflow.name = "test_workflow"
    workflow.status = "active"
    workflow.tags = ["tag1", "tag2"]
    workflow.count = 123
    workflow.numbers = [1, 2, 3]
    workflow.mixed_union = "string_value"
    workflow.string_union = "text"

    categorical_fields = workflow.get_categorical_fields()

    # Should detect string-based fields
    assert "name" in categorical_fields  # str
    assert "status" in categorical_fields  # Optional[str]
    assert "tags" in categorical_fields  # List[str]
    assert "string_union" in categorical_fields  # Union[str, bool]

    # Should not detect numeric fields
    assert "count" not in categorical_fields  # int
    assert "numbers" not in categorical_fields  # List[int]

    # Clean up
    workflow.__class__.model_fields = {}


def test_workflow_get_fields_with_none_values_in_model():
    """Test field detection when model_fields exist but actual values are None."""
    from typing import Optional

    from socm.core.models import Workflow

    class MockFieldInfo:
        def __init__(self, annotation):
            self.annotation = annotation

    workflow = Workflow(name="test", executable="test", context="test")

    workflow.__class__.model_fields = {
        "optional_int": MockFieldInfo(Optional[int]),
        "optional_str": MockFieldInfo(Optional[str]),
    }

    # Set values to None
    workflow.optional_int = None
    workflow.optional_str = None

    numeric_fields = workflow.get_numeric_fields()
    categorical_fields = workflow.get_categorical_fields()

    # Should not include None values even if type annotations suggest they could be numeric/categorical
    assert "optional_int" not in numeric_fields
    assert "optional_str" not in categorical_fields

    # Clean up
    workflow.__class__.model_fields = {}


def test_workflow_get_fields_type_checking_edge_cases():
    """Test edge cases in type checking logic."""
    from typing import List, Union

    from socm.core.models import Workflow

    class MockFieldInfo:
        def __init__(self, annotation):
            self.annotation = annotation

    workflow = Workflow(name="test", executable="test", context="test")

    # Test various edge cases in type checking
    workflow.__class__.model_fields = {
        "simple_list": MockFieldInfo(list),  # Non-parameterized list
        "empty_args": MockFieldInfo(List),  # List without type args
        "complex_nested": MockFieldInfo(List[List[int]]),  # Nested generic
        "non_iterable_origin": MockFieldInfo(Union[int, str]),  # Union is not iterable
    }

    workflow.simple_list = [1, 2, 3]
    workflow.empty_args = ["a", "b"]
    workflow.complex_nested = [[1, 2], [3, 4]]
    workflow.non_iterable_origin = 42

    _ = workflow.get_numeric_fields()
    _ = workflow.get_categorical_fields()

    # These should be handled gracefully without errors
    # Exact behavior depends on implementation details

    # Clean up
    workflow.__class__.model_fields = {}


def test_workflow_avoid_attributes_functionality():
    """Test that avoid_attributes parameter works correctly."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test", id=123)

    workflow.numeric_field = 456
    # Without avoid_attributes
    all_numeric = workflow.get_numeric_fields()
    assert "id" in all_numeric
    assert "numeric_field" not in all_numeric

    # With avoid_attributes
    filtered_numeric = workflow.get_numeric_fields(avoid_attributes=["id"])
    assert "id" not in filtered_numeric
    assert "numeric_field" not in filtered_numeric

    # Test categorical fields too
    all_categorical = workflow.get_categorical_fields()
    assert "name" in all_categorical

    filtered_categorical = workflow.get_categorical_fields(avoid_attributes=["name", "executable"])
    assert "name" not in filtered_categorical
    assert "executable" not in filtered_categorical
    assert "context" in filtered_categorical


def test_workflow_exception_handling_in_field_detection():
    """Test exception handling in get_numeric_fields and get_categorical_fields."""
    from socm.core.models import Workflow

    workflow = Workflow(name="test", executable="test", context="test")

    # Create problematic iterables that will cause exceptions in all() calls
    class ProblematicIterable:
        def __iter__(self):
            return self

        def __next__(self):
            raise TypeError("Intentional error for testing")

    class AnotherProblematicIterable:
        def __iter__(self):
            return self

        def __next__(self):
            raise ValueError("Intentional error for testing")

    # Set attributes that will trigger exceptions
    workflow.problematic_numeric = ProblematicIterable()
    workflow.problematic_categorical = AnotherProblematicIterable()
    workflow.another_problematic = ProblematicIterable()

    # These should not crash due to exception handling
    numeric_fields = workflow.get_numeric_fields()
    categorical_fields = workflow.get_categorical_fields()

    # The problematic fields should not be included due to exception handling
    assert "problematic_numeric" not in numeric_fields
    assert "problematic_categorical" not in categorical_fields
    assert "another_problematic" not in categorical_fields
