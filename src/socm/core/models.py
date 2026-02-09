from collections.abc import Iterable
from numbers import Number
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union, get_args, get_origin

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

if TYPE_CHECKING:
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
    _existing_jobs: Dict[str, List[Tuple[str, int, int]]] = PrivateAttr(default_factory=dict)

    def fits_in_qos(self, walltime: int, cores: int) -> QosPolicy | None:
        """
        Check if the given walltime and cores fit within the specified QoS policy.

        Args:
            walltime (int): The requested walltime in minutes.
            cores (int): The requested number of cores.

        Returns:
            QosPolicy | None: The matching QoS policy object or None if no match is found.
        """

        # What happens when the job does not fit in the best possible QoS?
        for policy in self.qos:
            existing_jobs = self._existing_jobs.get(policy.name, [])

            # Check walltime constraint (None means unlimited)
            if policy.max_walltime is not None and policy.max_walltime < walltime:
                continue

            # Check cores constraint (None means unlimited)
            if policy.max_cores is not None:
                remaining_cores = policy.max_cores - sum(job[2] for job in existing_jobs)
                if remaining_cores < cores:
                    continue

            # Check max jobs constraint (None means unlimited)
            if policy.max_jobs is not None and len(existing_jobs) >= policy.max_jobs:
                continue

            return policy
        return None

    def register_job(self, job_id: str, walltime: int, cores: int) -> bool:
        """
        Register a job with the resource if it fits within the QoS policies.

        Args:
            job_id (str): The unique identifier for the job.
            walltime (int): The requested walltime in minutes.
            cores (int): The requested number of cores.

        Returns:
            bool: True if the job was registered successfully, False otherwise.
        """
        qos_policy = self.fits_in_qos(walltime, cores)
        if qos_policy:
            qos_name = qos_policy.name
            existing_jobs = self._existing_jobs.get(qos_name, [])
            existing_jobs.append((job_id, walltime, cores))
            self._existing_jobs[qos_name] = existing_jobs
            return True
        return False

class Workflow(BaseModel):
    name: str
    executable: str = ""
    context: str = ""
    subcommand: str = ""
    id: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    resources: Optional[Dict[str, int | float]] = None
    depends: Optional[List[str]] = None
    model_config = {
        "extra": "allow",
    }

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Workflow):
            return self.id == other.id
        return NotImplemented

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

    def get_tasks(self) -> List["TaskDescription"]:
        """
        Returns a list of TaskDescription objects for the workflow.
        This is a placeholder method and should be implemented in subclasses.
        """
        raise NotImplementedError("This method should be implemented in subclasses")


class DAG(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    graph: nx.DiGraph = Field(default_factory=nx.DiGraph)

    def add_workflow(self, workflow: Workflow):
        self.graph.add_node(workflow.id, workflow=workflow)

    def add_dependency(self, parent_id: int, child_id: int):
        self.graph.add_edge(parent_id, child_id)

    @property
    def workflows(self) -> List[Workflow]:
        """Return workflows in topological order."""
        return [self.graph.nodes[n]["workflow"] for n in nx.topological_sort(self.graph)]

    def __iter__(self):
        return iter(self.workflows)

    def __len__(self):
        return self.graph.number_of_nodes()

    def __getitem__(self, idx):
        return self.workflows[idx]


class Campaign(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: int
    workflows: DAG
    deadline: str
    target_resource: str = "tiger3"
    campaign_policy: str = "time"
    execution_schema: str = "batch"
    requested_resources: int = 0

    @field_validator("workflows", mode="before")
    @classmethod
    def validate_workflows(cls, v):
        if isinstance(v, list):
            dag = DAG()
            for w in v:
                dag.add_workflow(w)
            name_to_id = {w.name: w.id for w in v}
            for w in v:
                if w.depends:
                    for dep_name in w.depends:
                        if dep_name in name_to_id:
                            dag.add_dependency(name_to_id[dep_name], w.id)
            return dag
        return v
