from collections.abc import Iterable
from numbers import Number
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union, get_args, get_origin

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

if TYPE_CHECKING:
    from radical.pilot import TaskDescription


class QosPolicy(BaseModel):
    """
    SLURM Quality of Service policy defining per-queue job limits.

    Each QoS policy corresponds to a named SLURM QoS tier. The planner uses
    these policies to select the most restrictive (shortest walltime) tier that
    still satisfies a workflow's resource and time requirements.

    Parameters
    ----------
    name : str
        The SLURM QoS name (e.g. ``"short"``, ``"regular"``).
    max_walltime : int or None, optional
        Maximum allowed walltime in minutes. ``None`` means unlimited.
    max_jobs : int or None, optional
        Maximum number of concurrent jobs. ``None`` means unlimited.
    max_cores : int or None, optional
        Maximum total core count that can be requested at once. ``None`` means unlimited.
    """

    name: str
    max_walltime: Optional[int] = None  # in minutes
    max_jobs: Optional[int] = None
    max_cores: Optional[int] = None


class Resource(BaseModel):
    """
    HPC resource definition with node, core, and memory specifications plus QoS policies.

    A ``Resource`` describes a complete HPC system. Subclasses (e.g. ``TigerResource``)
    pre-populate the QoS list for a specific cluster. The planner uses the QoS list
    and the core/memory limits to schedule workflows into appropriate tiers.

    Parameters
    ----------
    name : str
        Unique identifier for the resource, e.g. ``"tiger3"``.
    nodes : int
        Total number of compute nodes available on the system.
    cores_per_node : int
        Number of CPU cores on each compute node.
    memory_per_node : int
        Amount of memory per node in megabytes.
    qos : list of QosPolicy, optional
        Ordered list of QoS policies from most to least restrictive.
        The planner iterates this list in order and selects the first
        policy that fits the requested walltime and core count.
    """

    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int
    qos: List[QosPolicy] = Field(default_factory=list)
    _existing_jobs: Dict[str, List[Tuple[str, int, int]]] = PrivateAttr(default_factory=dict)

    def fits_in_qos(self, walltime: int, cores: int) -> QosPolicy | None:
        """
        Find the first QoS policy that can accommodate the given walltime and core count.

        Iterates over the ordered QoS list and returns the first policy whose
        walltime, core, and job limits are not exceeded. Jobs already registered
        via :meth:`register_job` are accounted for when checking the core limit.

        Parameters
        ----------
        walltime : int
            Requested walltime in minutes.
        cores : int
            Requested number of cores.

        Returns
        -------
        QosPolicy or None
            The first matching QoS policy, or ``None`` if no policy fits.
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

        Calls :meth:`fits_in_qos` to find an appropriate policy and, if one is
        found, records the job under that policy's name so that subsequent calls
        account for the consumed capacity.

        Parameters
        ----------
        job_id : str
            A unique identifier for the job (used as a key in the internal
            tracking dictionary).
        walltime : int
            Requested walltime in minutes.
        cores : int
            Requested number of cores.

        Returns
        -------
        bool
            ``True`` if the job was successfully registered, ``False`` if no
            QoS policy can accommodate the request.
        """
        qos_policy = self.fits_in_qos(walltime, cores)
        if qos_policy:
            qos_name = qos_policy.name
            existing_jobs = self._existing_jobs.get(qos_name, [])
            existing_jobs.append((job_id, walltime, cores))
            self._existing_jobs[qos_name] = existing_jobs
            return True
        return False


class ResourceSpec(BaseModel):
    """
    Per-workflow resource specification used by the enactor when building task descriptions.

    Extra fields beyond the declared ones are allowed (``extra = "allow"``), so
    workflow subclasses can store additional resource attributes such as
    ``memory`` without redefining this model.

    Parameters
    ----------
    ranks : int, optional
        Number of MPI ranks (processes) to request. Defaults to 1.
    threads : int, optional
        Number of OpenMP threads per rank. Defaults to 1.
    runtime : float, optional
        Requested runtime in minutes. Defaults to 60.
    """

    ranks: int = 1
    threads: int = 1
    runtime: float = 60

    model_config = {
        "extra": "allow",
    }

    def __getitem__(self, item):
        return getattr(self, item)


class Workflow(BaseModel):
    """
    Base class for all workflow types.

    Defines the common fields and interface that every workflow in the campaign
    manager must implement. Subclasses must override :meth:`get_command` and
    :meth:`get_arguments` and be registered in ``registered_workflows`` in
    ``socm.workflows`` to be usable from TOML configuration files.

    Parameters
    ----------
    name : str
        Human-readable name for this workflow instance.
    executable : str, optional
        The executable to invoke (e.g. ``"so-site-pipeline"``). Defaults to ``""``.
    context : str, optional
        Path or URI to the sotodlib context file. Defaults to ``""``.
    subcommand : str, optional
        Sub-command passed to the executable (e.g. ``"make-ml-map"``). Defaults to ``""``.
    id : int or None, optional
        Unique integer ID assigned by the campaign manager. Defaults to ``None``.
    environment : dict of str to str or None, optional
        Environment variables to set during execution. Defaults to ``None``.
    resources : ResourceSpec, optional
        Resource requirements (ranks, threads, runtime). Defaults to a
        ``ResourceSpec`` with all default values.
    depends : list of str, optional
        Names of workflows that must complete before this one can start.
        Defaults to an empty list.

    Notes
    -----
    Extra Pydantic fields are allowed (``extra = "allow"``), enabling
    workflow-specific parameters to be declared directly on subclasses or
    passed through TOML configuration without schema errors.
    """

    name: str
    executable: str = ""
    context: str = ""
    subcommand: str = ""
    id: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    depends: List[str] = []

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
        """
        Return the full shell command string to execute this workflow.

        Must be overridden by every concrete workflow subclass.

        Returns
        -------
        str
            The complete command, including the executable, subcommand, and
            any fixed flags required to invoke the workflow.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_arguments(self, **kargs) -> List[str]:
        """
        Return the command-line arguments for this workflow as a list of strings.

        Must be overridden by every concrete workflow subclass.

        Returns
        -------
        list of str
            Ordered list of argument strings (positional and/or ``--key=value``
            pairs) to be appended to the command returned by :meth:`get_command`.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_numeric_fields(self, avoid_attributes: List[str] | None = None) -> List[str]:
        """
        Return field names whose values are numeric types or numeric iterables.

        Uses Pydantic v2 ``model_fields`` for declared fields and also inspects
        ``model_extra`` for dynamically added numeric attributes.

        Parameters
        ----------
        avoid_attributes : list of str or None, optional
            Field names to exclude from the result. Defaults to ``None``
            (no exclusions).

        Returns
        -------
        list of str
            Names of fields whose declared annotation or actual value is a
            :class:`numbers.Number` or an iterable of numbers.
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
        # Include model_extra for Pydantic v2 extra="allow" fields
        extra = getattr(self, 'model_extra', None) or {}
        all_attrs = {**self.__dict__, **extra}
        for field_name, value in all_attrs.items():
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
        Return field names whose values are string types or string iterables.

        Uses Pydantic v2 ``model_fields`` for declared fields and also inspects
        ``model_extra`` for dynamically added string attributes.

        Parameters
        ----------
        avoid_attributes : list of str or None, optional
            Field names to exclude from the result. Defaults to ``None``
            (no exclusions).

        Returns
        -------
        list of str
            Names of fields whose declared annotation or actual value is a
            :class:`str` or an iterable of strings.
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

        # Also check actual instance values for categorical fields not captured by annotations
        # Include model_extra for Pydantic v2 extra="allow" fields
        extra = getattr(self, 'model_extra', None) or {}
        all_attrs = {**self.__dict__, **extra}
        for field_name, value in all_attrs.items():
            if field_name not in categorical_fields and field_name not in avoid_attributes:
                if isinstance(value, str):
                    categorical_fields.append(field_name)
                elif isinstance(value, Iterable) and not isinstance(value, (Number, bytes, dict)):
                    # Check if all elements are strings
                    try:
                        if all(isinstance(item, str) for item in value):
                            categorical_fields.append(field_name)
                    except (TypeError, ValueError):
                        pass

        return categorical_fields

    def get_tasks(self) -> List["TaskDescription"]:
        """
        Return a list of RADICAL-Pilot ``TaskDescription`` objects for the workflow.

        Must be overridden by concrete workflow subclasses that need direct
        RADICAL-Pilot task control. The base implementation always raises
        :class:`NotImplementedError`.

        Returns
        -------
        list of TaskDescription
            Task descriptions suitable for submission via a RADICAL-Pilot
            ``TaskManager``.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("This method should be implemented in subclasses")


class DAG(BaseModel):
    """
    Directed Acyclic Graph of workflows with dependency edges.

    Wraps a ``networkx.DiGraph`` to manage workflow nodes and their
    dependency relationships. Workflows are stored as node attributes keyed
    by their integer ``id``. The class provides iteration in topological order
    and level-based grouping for parallel scheduling.

    Parameters
    ----------
    graph : networkx.DiGraph, optional
        Underlying directed graph. Defaults to an empty ``DiGraph``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    graph: nx.DiGraph = Field(default_factory=nx.DiGraph)

    def add_workflow(self, workflow: Workflow):
        """
        Add a workflow as a node in the DAG.

        Parameters
        ----------
        workflow : Workflow
            The workflow to add. Its ``id`` is used as the node key.
        """
        self.graph.add_node(workflow.id, workflow=workflow)

    def add_dependency(self, parent_id: int, child_id: int):
        """
        Add a directed dependency edge from a parent workflow to a child workflow.

        Parameters
        ----------
        parent_id : int
            ID of the workflow that must complete first.
        child_id : int
            ID of the workflow that depends on the parent.
        """
        self.graph.add_edge(parent_id, child_id)

    @property
    def workflows(self) -> List[Workflow]:
        """
        Return all workflows in topological order.

        Returns
        -------
        list of Workflow
            Workflows sorted so that every dependency appears before the
            workflow that depends on it.
        """
        return [self.graph.nodes[n]["workflow"] for n in nx.topological_sort(self.graph)]

    @property
    def levels(self) -> List[List[Workflow]]:
        """
        Return workflows grouped by dependency level (generation).

        Each level contains workflows whose dependencies are all satisfied
        by previous levels, and can therefore be executed in parallel.

        Returns
        -------
        list of list of Workflow
            Outer list represents levels from earliest to latest; inner lists
            contain workflows that may run concurrently within that level.
        """
        return [
            [self.graph.nodes[n]["workflow"] for n in generation]
            for generation in nx.topological_generations(self.graph)
        ]

    def __iter__(self):
        return iter(self.workflows)

    def get_id_by_name(self, workflow_name: str) -> int | None:
        """
        Look up a workflow's integer ID by its name.

        Parameters
        ----------
        workflow_name : str
            The ``name`` attribute of the workflow to find.

        Returns
        -------
        int or None
            The workflow's ``id``, or ``None`` if no workflow with that name
            exists in the DAG.
        """
        for workflow in self.workflows:
            if workflow.name == workflow_name:
                return workflow.id

        return None

    def __len__(self):
        return self.graph.number_of_nodes()

    def __getitem__(self, idx):
        return self.workflows[idx]

    def __repr__(self):
        return f"DAG({self.workflows})"


class Campaign(BaseModel):
    """
    A collection of workflows to be executed as a single campaign.

    Contains the workflow DAG, scheduling policy, target resource, and
    deadline constraints. When constructed from a plain list of
    :class:`Workflow` objects the ``workflows`` field validator automatically
    builds the :class:`DAG` and wires up dependency edges from each workflow's
    ``depends`` list.

    Parameters
    ----------
    id : int
        Unique integer campaign identifier.
    workflows : DAG or list of Workflow
        The workflows to execute. A plain list is automatically converted
        to a :class:`DAG` with dependency edges derived from each workflow's
        ``depends`` field.
    deadline : str
        Campaign deadline as a human-readable string (e.g. ``"2d"``). The
        bookkeeper converts this to a numeric objective for the planner.
    target_resource : str, optional
        Key used to look up the resource in ``registered_resources``.
        Defaults to ``"tiger3"``.
    campaign_policy : str, optional
        Scheduling policy passed to the planner. Defaults to ``"time"``.
    execution_schema : str, optional
        Execution schema, either ``"batch"`` or ``"remote"``. Defaults to
        ``"batch"``.
    requested_resources : int, optional
        Total number of cores to request when using batch execution.
        Defaults to ``0``.
    """

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
        """
        Convert a list of workflows into a DAG, wiring dependency edges.

        Parameters
        ----------
        v : list of Workflow or DAG
            If a list, each workflow's ``depends`` field is used to create
            directed edges in the new DAG. If already a :class:`DAG`, it is
            returned unchanged.

        Returns
        -------
        DAG
            The validated workflow DAG.
        """
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


class PlanEntry(NamedTuple):
    """
    A single scheduled workflow entry in the execution plan.

    Attributes
    ----------
    workflow : Workflow
        The workflow to execute.
    cores : range
        The range of core indices allocated to this workflow.
    memory : float
        Memory allocated to this workflow in megabytes.
    start_time : float
        Scheduled start time in minutes from the beginning of the campaign.
    end_time : float
        Scheduled end time in minutes from the beginning of the campaign.
    """

    workflow: Workflow
    cores: range
    memory: float
    start_time: float
    end_time: float


class Batch(NamedTuple):
    """
    A group of workflows that execute within a single pilot submission.

    Batches are created when the campaign deadline exceeds the maximum
    walltime of a single QoS tier, requiring the plan to be split into
    sequential pilot allocations.

    Attributes
    ----------
    plan : list of PlanEntry
        The scheduled workflow entries belonging to this batch.
    graph : networkx.DiGraph
        Intra-batch dependency graph (cross-batch edges are dropped because
        sequential batch execution already enforces ordering).
    """

    plan: List[PlanEntry]
    graph: nx.DiGraph


class PlanResult(NamedTuple):
    """
    Complete output of the planning phase.

    Attributes
    ----------
    qos : QosPolicy or None
        The selected SLURM QoS policy. ``None`` when using batch execution
        schema, where the resource allocation is fully controlled by the user.
    ncores : int
        Total number of cores to request for the pilot job.
    batches : list of Batch
        One or more batches of scheduled workflows. A single-element list
        means the entire campaign fits within one pilot submission.
    """

    qos: Optional[QosPolicy]  # None for batch execution schema
    ncores: int
    batches: List[Batch]  # Length 1 for single-submission campaigns
