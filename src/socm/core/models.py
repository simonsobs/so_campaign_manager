from collections.abc import Iterable
from numbers import Number
from typing import Dict, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, Field
from radical.pilot import TaskDescription


class QosPolicy(BaseModel):
    name: str
    max_walltime: Optional[int] = None  # in minutes
    max_jobs: Optional[int] = None
    max_cores: Optional[int] = None


class Resource(BaseModel):
    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int
    qos: List[QosPolicy] = Field(default_factory=list)


class Workflow(BaseModel):
    name: str
    executable: str
    context: str
    subcommand: str = ""
    id: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    resources: Optional[Dict[str, int | float]] = None

    model_config = {
        "extra": "allow",
    }

    def get_command(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_arguments(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_numeric_fields(self, avoid_attributes: List[str] | None = None) -> List[str]:
        """
        Returns a list of field names that are either numeric types
        or iterable collections of numeric types.

        Uses Pydantic v2 model_fields for type introspection.

        Returns:
            List[str]: Field names with numeric values
        """
        if avoid_attributes is None:
            avoid_attributes = []

        numeric_fields = []

        # Get field information from Pydantic v2 model_fields
        for field_name, field_info in self.__class__.model_fields.items():
            # Get the annotation type
            if field_name in avoid_attributes or getattr(self, field_name) is None:
                continue
            field_type = field_info.annotation

            # Check for direct numeric types
            if isinstance(field_type, type) and issubclass(field_type, Number):
                numeric_fields.append(field_name)
                continue

            # Check for complex types (Optional, List, etc)
            origin = get_origin(field_type)
            if origin is not None:
                args = get_args(field_type)

                # Check for Optional numeric types
                if origin is Union:
                    for arg in args:
                        if isinstance(arg, type) and issubclass(arg, Number):
                            numeric_fields.append(field_name)
                            break
                # Check for iterables of numbers
                elif issubclass(origin, Iterable):
                    # Check if it's a parameterized generic like List[int]
                    if args and len(args) > 0:
                        element_type = args[0]
                        if isinstance(element_type, type) and issubclass(element_type, Number):
                            numeric_fields.append(field_name)

        # Also check actual instance values for numeric fields not captured by annotations
        for field_name, value in self.__dict__.items():
            if field_name not in numeric_fields and field_name not in avoid_attributes:
                if isinstance(value, Number):
                    numeric_fields.append(field_name)
                elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
                    # Check if all elements are numbers
                    try:
                        if all(isinstance(item, Number) for item in value):
                            numeric_fields.append(field_name)
                    except (TypeError, ValueError):
                        pass

        return numeric_fields

    def get_categorical_fields(self, avoid_attributes: List[str] | None = None) -> List[str]:
        """
        Returns a list of field names that are either string types
        or iterable collections of string types.

        Uses Pydantic v2 model_fields for type introspection.

        Returns:
            List[str]: Field names with categorical (string) values
        """
        if avoid_attributes is None:
            avoid_attributes = []
        categorical_fields = []

        # Get field information from Pydantic v2 model_fields
        for field_name, field_info in self.__class__.model_fields.items():
            # Get the annotation type
            if field_name in avoid_attributes or getattr(self, field_name) is None:
                continue
            field_type = field_info.annotation

            # Check for direct numeric types
            if isinstance(field_type, type) and issubclass(field_type, str):
                categorical_fields.append(field_name)
                continue

            # Check for complex types (Optional, List, etc)
            origin = get_origin(field_type)
            if origin is not None:
                args = get_args(field_type)

                # Check for Optional numeric types
                if origin is Union:
                    for arg in args:
                        if isinstance(arg, type) and issubclass(arg, str):
                            categorical_fields.append(field_name)
                            break
                # Check for iterables of numbers
                elif issubclass(origin, Iterable):
                    # Check if it's a parameterized generic like List[int]
                    if args and len(args) > 0:
                        element_type = args[0]
                        if isinstance(element_type, type) and issubclass(element_type, str):
                            categorical_fields.append(field_name)

        # Also check actual instance values for numeric fields not captured by annotations
        for field_name, value in self.__dict__.items():
            if field_name not in categorical_fields and field_name not in avoid_attributes:
                if isinstance(value, str):
                    categorical_fields.append(field_name)
                elif isinstance(value, Iterable) and not isinstance(value, (Number, bytes, dict)):
                    # Check if all elements are numbers
                    try:
                        if all(isinstance(item, str) for item in value):
                            categorical_fields.append(field_name)
                    except (TypeError, ValueError):
                        pass

        return categorical_fields

    def get_tasks(self) -> List[TaskDescription]:
        """
        Returns a list of TaskDescription objects for the workflow.
        This is a placeholder method and should be implemented in subclasses.
        """
        raise NotImplementedError("This method should be implemented in subclasses")


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    deadline: str
    target_resource: str = "tiger3"
    campaign_policy: str = "time"
    execution_schema: str = "batch"
    requested_resources: int = 0
