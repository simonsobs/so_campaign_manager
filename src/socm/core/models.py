from typing import Dict, List, Optional, get_origin, get_args, Union
from numbers import Number
from collections.abc import Iterable

from pydantic import BaseModel


class Resource(BaseModel):
    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int
    default_queue: str = "normal"
    maximum_walltime: int = 1440


class Workflow(BaseModel):
    name: str
    executable: str
    context: str
    subcommand: str
    id: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    resources: Optional[Dict[str, int]] = None

    model_config = {
        "extra": "allow",
    }

    def get_command(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_arguments(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_numeric_fields(self) -> List[str]:
        """
        Returns a list of field names that are either numeric types
        or iterable collections of numeric types.

        Uses Pydantic v2 model_fields for type introspection.

        Returns:
            List[str]: Field names with numeric values
        """
        numeric_fields = []

        # Get field information from Pydantic v2 model_fields
        for field_name, field_info in self.__class__.model_fields.items():
            # Get the annotation type
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
            if field_name not in numeric_fields:
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


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    deadline: str
    resource: str = "tiger3"
