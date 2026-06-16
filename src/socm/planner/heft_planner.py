from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

from ..core import DAG, Batch, Campaign, PlanEntry, PlanResult, QosPolicy, Resource
from .base import Planner


class HeftPlanner(Planner):
    """
    Campaign planner using the Heterogeneous Earliest Finish Time (HEFT) algorithm.

    HEFT is a list-scheduling algorithm that minimises overall makespan by
    assigning workflows to the processor slot that yields the earliest finish
    time, respecting both data dependencies and memory constraints.

    The planner supports two execution schemas:

    * **batch** — Fixed resource allocation: the caller specifies the total
      core count and the plan is produced as a single batch with no QoS
      matching.
    * **remote** — Optimised allocation: a binary search finds the minimum
      number of cores that satisfies the campaign deadline, then the plan is
      matched against the resource's QoS policies.  If no single QoS tier
      covers both the required cores and the full deadline, the plan is split
      into sequential batches that each fit within the best available tier.

    Reference
    ---------
    Topcuoglu, H., Hariri, S., & Wu, M. Y. (2002). Performance-effective and
    low-complexity task scheduling for heterogeneous computing.
    *IEEE Transactions on Parallel and Distributed Systems*, 13(3), 260–274.

    Parameters
    ----------
    campaign : Campaign or None, optional
        The campaign object. May be passed here or directly to :meth:`plan`.
    resources : Resource or None, optional
        The HPC resource description.
    resource_requirements : dict of int to dict, or None, optional
        Per-workflow resource requirements (see :class:`~socm.planner.base.Planner`).
    policy : str or None, optional
        Scheduling policy string (reserved for future use).
    sid : str or None, optional
        Session ID for logger namespacing.
    objective : int or None, optional
        Campaign makespan objective in minutes.

    Attributes
    ----------
    _estimated_walltime : list of float
        Estimated walltimes (minutes) for the workflows scheduled in the last
        call to :meth:`_calculate_plan`.
    _estimated_cpus : list of int
        Estimated CPU counts for the same workflows.
    _estimated_memory : list of float
        Estimated memory requirements (MB) for the same workflows.
    """

    def __init__(
        self,
        campaign: Campaign | None = None,
        resources: Resource | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        policy: str | None = None,
        sid: str | None = None,
        objective: int | None = None
    ):
        super().__init__(
            campaign=campaign,
            resources=resources,
            resource_requirements=resource_requirements,
            sid=sid,
            policy=policy,
            objective=objective
        )
        # Initialize estimation tables (populated during planning)
        self._estimated_walltime: List[float] = []
        self._estimated_cpus: List[int] = []
        self._estimated_memory: List[float] = []

    def _get_free_memory(self, start_time: float, num_nodes: float) -> float:
        """
        Calculate available memory at a given simulation time.

        Sums the memory of all plan entries that overlap ``start_time`` and
        subtracts from the total memory of the requested nodes.

        Parameters
        ----------
        start_time : float
            The time point (in minutes) at which to check memory availability.
        num_nodes : float
            The number of nodes being considered for the new workflow.

        Returns
        -------
        float
            Available memory in megabytes at ``start_time``.
        """
        total_memory = num_nodes * self._resources.memory_per_node
        used_memory = sum(
            entry.memory
            for entry in self._plan
            if entry.start_time <= start_time < entry.end_time
        )
        return total_memory - used_memory

    def _get_max_ncores(self, resource_requirements: Dict[int, Dict[str, float]]) -> int:
        """
        Return the maximum core count required by any single workflow.

        Parameters
        ----------
        resource_requirements : dict of int to dict
            Per-workflow resource requirements, each containing ``req_cpus``.

        Returns
        -------
        int
            The largest ``req_cpus`` value across all workflows.
        """
        return max(values["req_cpus"] for values in resource_requirements.values())

    def _find_suitable_qos_policies(self, requested_cores: int) -> QosPolicy:
        """
        Find the first QoS policy that can accommodate the campaign deadline.

        Delegates to :meth:`~socm.core.models.Resource.fits_in_qos`. Raises
        :class:`ValueError` if no policy satisfies the constraints.

        Parameters
        ----------
        requested_cores : int
            The number of cores to check against each policy's core limit.

        Returns
        -------
        QosPolicy
            The first suitable QoS policy.

        Raises
        ------
        ValueError
            If no QoS policy can accommodate the campaign deadline with the
            requested core count.
        """
        suitable_qos = self._resources.fits_in_qos(self._objective, cores=requested_cores)
        if not suitable_qos:
            available_qos = ', '.join(f"{q.name}({q.max_walltime}min)" for q in self._resources.qos)
            raise ValueError(
                f"No QoS policy can accommodate deadline of {self._objective} minutes. "
                f"Available policies: {available_qos}"
            )

        return suitable_qos

    def _binary_search_resources(
        self,
        campaign: DAG,
        resource_requirements: Dict[int, Dict[str, float]],
        lower_bound: int,
        upper_bound: int
    ) -> Tuple[int, List[PlanEntry], nx.DiGraph] | None:
        """
        Binary-search for the minimum core count that satisfies the campaign deadline.

        Calls :meth:`_calculate_plan` at each midpoint and retains the result
        if the maximum finish time does not exceed :attr:`_objective`.

        Parameters
        ----------
        campaign : DAG
            The workflow DAG to schedule.
        resource_requirements : dict of int to dict
            Per-workflow resource requirements.
        lower_bound : int
            Minimum number of cores to consider (usually the largest single
            workflow's ``req_cpus``).
        upper_bound : int
            Maximum number of cores to consider (usually ``requested_resources``).

        Returns
        -------
        tuple of (int, list of PlanEntry, networkx.DiGraph) or None
            A 3-tuple of ``(ncores, plan, graph)`` for the minimum feasible
            core count, or ``None`` if no allocation within the bounds
            satisfies the deadline.
        """
        best_ncores = None
        best_plan = None
        best_graph = None

        while lower_bound <= upper_bound:
            mid = (lower_bound + upper_bound) // 2

            test_plan, test_graph = self._calculate_plan(
                campaign=campaign,
                resources=range(mid),
                resource_requirements=resource_requirements
            )

            max_finish_time = max(entry.end_time for entry in test_plan)

            if max_finish_time <= self._objective:
                # This works! Try with fewer resources
                best_ncores = mid
                best_plan = test_plan
                best_graph = test_graph
                upper_bound = mid - 1
            else:
                # Need more resources
                lower_bound = mid + 1

        if best_ncores is not None:
            return best_ncores, best_plan, best_graph
        return None

    def _build_batch_subgraph(self, graph: nx.DiGraph, workflow_ids: List[int | None]) -> nx.DiGraph:
        """
        Extract the intra-batch subgraph, dropping any cross-batch dependency edges.

        Parameters
        ----------
        graph : networkx.DiGraph
            The full plan dependency graph.
        workflow_ids : list of int or None
            Workflow IDs belonging to this batch.

        Returns
        -------
        networkx.DiGraph
            A new directed graph containing only the nodes from
            ``workflow_ids`` and the edges between them.
        """
        id_set = set(workflow_ids)
        subgraph = nx.DiGraph()
        for wf_id in workflow_ids:
            subgraph.add_node(wf_id)
        for wf_id in workflow_ids:
            for successor in graph.successors(wf_id):
                if successor in id_set:
                    subgraph.add_edge(wf_id, successor)
        return subgraph

    def _split_plan_into_batches(
        self, plan: List[PlanEntry], graph: nx.DiGraph, max_walltime: float
    ) -> List[Batch]:
        """
        Split a full execution plan into sequential batches bounded by ``max_walltime``.

        Entries are assigned to batches greedily, sorted by end time. A new
        batch begins when the next entry's end time would exceed the current
        batch window. Cross-batch dependency edges are dropped because
        sequential batch execution already guarantees ordering.

        Parameters
        ----------
        plan : list of PlanEntry
            The full list of scheduled plan entries. Sorted internally by
            end time.
        graph : networkx.DiGraph
            The full dependency graph for the plan.
        max_walltime : float
            Maximum duration (in the same time units as ``PlanEntry`` times)
            allowed per batch.

        Returns
        -------
        list of Batch
            Ordered list of batches; each batch fits within ``max_walltime``.
        """
        sorted_plan = sorted(plan, key=lambda e: e.end_time)
        batches: List[Batch] = []
        current_batch: List[PlanEntry] = []
        batch_start = 0.0

        for entry in sorted_plan:
            tentative_start = min(batch_start, entry.start_time) if current_batch else entry.start_time

            if entry.end_time > tentative_start + max_walltime:
                if current_batch:
                    batch_wf_ids = [e.workflow.id for e in current_batch]
                    batches.append(Batch(
                        plan=current_batch,
                        graph=self._build_batch_subgraph(graph, batch_wf_ids)
                    ))
                batch_start = entry.start_time
                current_batch = []
            else:
                batch_start = tentative_start

            current_batch.append(entry)

        if current_batch:
            batch_wf_ids = [e.workflow.id for e in current_batch]
            batches.append(Batch(
                plan=current_batch,
                graph=self._build_batch_subgraph(graph, batch_wf_ids)
            ))

        return batches

    def _plan_with_qos_optimization(
        self,
        campaign: DAG,
        resource_requirements: Dict[int, Dict[str, float]],
        requested_resources: int,
    ) -> PlanResult:
        """
        Find the optimal QoS tier and resource allocation for the campaign.

        Performs a binary search (via :meth:`_binary_search_resources`) for
        the minimum core count that meets the deadline. If a single QoS tier
        covers both the required cores and the full deadline, the plan is
        returned as a single batch. Otherwise the plan is split into multiple
        sequential batches using the QoS tier with the highest walltime that
        still supports the required core count.

        Parameters
        ----------
        campaign : DAG
            The workflow DAG to schedule.
        resource_requirements : dict of int to dict
            Per-workflow resource requirements.
        requested_resources : int
            Upper bound on the core count to consider.

        Returns
        -------
        PlanResult
            Contains the selected QoS policy, the chosen core count, and one
            or more :class:`~socm.core.models.Batch` objects.

        Raises
        ------
        ValueError
            If the deadline cannot be met with ``requested_resources`` cores,
            if no QoS policy has a sufficient core limit, or if an individual
            workflow's duration exceeds the best-available QoS walltime.
        """
        max_workflow_resources = self._get_max_ncores(resource_requirements)
        upper_bound = requested_resources
        lower_bound = max_workflow_resources

        result = self._binary_search_resources(
            campaign, resource_requirements, lower_bound, upper_bound
        )

        if result is None:
            raise ValueError(
                f"Cannot meet {self._objective} min deadline with {requested_resources} cores. "
                f"Please increase deadline or increase requested cores."
            )

        ncores, plan, plan_graph = result

        # Try single-QoS fit (deadline fits within one pilot)
        qos_candidate = self._resources.fits_in_qos(self._objective, cores=ncores)
        if qos_candidate is not None:
            self._logger.info(
                f"Plan fits in single QoS {qos_candidate.name} with {ncores} cores"
            )
            return PlanResult(
                qos=qos_candidate,
                ncores=ncores,
                batches=[Batch(plan=plan, graph=plan_graph)]
            )

        # No single QoS fits — find best QoS by walltime among those with enough cores
        splittable = [
            q for q in self._resources.qos
            if q.max_cores is None or q.max_cores >= ncores
        ]
        if not splittable:
            available_qos = ', '.join(f"{q.name}(max_cores={q.max_cores})" for q in self._resources.qos)
            raise ValueError(
                f"No QoS policy has max_cores >= {ncores}. "
                f"Campaign is infeasible. Available: {available_qos}"
            )

        best_qos = max(
            splittable,
            key=lambda q: q.max_walltime if q.max_walltime is not None else float('inf')
        )
        max_walltime = best_qos.max_walltime or float('inf')

        # Validate that no individual workflow exceeds the batch window
        for entry in plan:
            wf_duration = entry.end_time - entry.start_time
            if wf_duration > max_walltime:
                raise ValueError(
                    f"Workflow '{entry.workflow.name}' requires {wf_duration:.1f} min, "
                    f"which exceeds QoS '{best_qos.name}' max walltime of {max_walltime} min. "
                    "Campaign is infeasible."
                )

        batches = self._split_plan_into_batches(plan, plan_graph, max_walltime)
        self._logger.info(
            f"Plan split into {len(batches)} batches using QoS {best_qos.name} "
            f"(max_walltime={max_walltime} min) with {ncores} cores"
        )
        return PlanResult(qos=best_qos, ncores=ncores, batches=batches)

    def _get_plan_graph(
        self, plan: List[PlanEntry], resources: range
    ) -> nx.DiGraph:
        """
        Build a dependency graph from the scheduled execution plan.

        For each plan entry, the method identifies which previously scheduled
        workflows occupied the same cores and adds directed edges from those
        predecessors to the current workflow.

        Parameters
        ----------
        plan : list of PlanEntry
            The scheduled plan entries in scheduling order.
        resources : range
            The full range of core indices used in the plan.

        Returns
        -------
        networkx.DiGraph
            A directed acyclic graph where each node is a workflow ID and each
            edge represents a resource-ordering dependency.
        """
        self._logger.debug("Create resource dependency DAG")
        graph = nx.DiGraph()

        # Track which workflow is using each core
        core_dependencies = {i: None for i in range(len(resources))}

        for entry in plan:
            # Find all previous tasks that occupied these cores
            previous_tasks = {
                core_dependencies[core]
                for core in entry.cores
                if core_dependencies[core] is not None
            }

            # Update core ownership
            for core in entry.cores:
                core_dependencies[core] = entry.workflow.id

            # Add node and edges to graph
            if not previous_tasks:
                graph.add_node(entry.workflow.id)
            else:
                for predecessor_id in previous_tasks:
                    graph.add_edge(predecessor_id, entry.workflow.id)

        self._logger.info(f"Calculated graph {graph}")
        return graph

    def plan(
        self,
        campaign: DAG | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        execution_schema: str | None = None,
        requested_resources: int | None = None
    ) -> PlanResult:
        """
        Plan campaign execution with QoS-aware resource allocation.

        Dispatches to :meth:`_plan_batch_mode` or
        :meth:`_plan_with_qos_optimization` depending on ``execution_schema``.

        Parameters
        ----------
        campaign : DAG or None, optional
            The workflow DAG to schedule.
        resource_requirements : dict of int to dict, or None, optional
            Per-workflow resource requirements keyed by workflow ID, each
            containing ``req_cpus``, ``req_memory``, and ``req_walltime``.
        execution_schema : str or None, optional
            ``"batch"`` uses ``requested_resources`` directly without QoS
            matching; any other value triggers QoS-optimised allocation.
        requested_resources : int or None, optional
            Total number of cores to use (batch mode) or the upper bound for
            binary search (remote mode).

        Returns
        -------
        PlanResult
            Contains the selected QoS policy (``None`` for batch mode), the
            total core count, and one or more :class:`~socm.core.models.Batch`
            objects representing pilot submissions.
        """
        if execution_schema == "batch":
            return self._plan_batch_mode(campaign, resource_requirements, requested_resources)
        else:
            return self._plan_with_qos_optimization(campaign, resource_requirements, requested_resources)

    def _plan_batch_mode(
        self,
        campaign: DAG,
        resource_requirements: Dict[int, Dict[str, float]],
        requested_resources: int
    ) -> PlanResult:
        """
        Plan execution for batch mode with a fixed, user-specified core count.

        Produces a single batch using exactly ``requested_resources`` cores
        and no QoS selection (``qos=None`` in the result).

        Parameters
        ----------
        campaign : DAG
            The workflow DAG to schedule.
        resource_requirements : dict of int to dict
            Per-workflow resource requirements.
        requested_resources : int
            Total number of cores to allocate.

        Returns
        -------
        PlanResult
            A single-batch result with ``qos=None`` and the full plan.
        """
        plan, plan_graph = self._calculate_plan(
            campaign=campaign,
            resources=range(requested_resources),
            resource_requirements=resource_requirements
        )
        self._logger.info(f"Plan to execute {plan} with {requested_resources} cores")
        return PlanResult(qos=None, ncores=requested_resources, batches=[Batch(plan=plan, graph=plan_graph)])

    def _initialize_resource_estimates(self, resource_requirements: Dict[int, Dict[str, float]], widxs: List[int]
    ) -> Dict[str, List[float]]:
        """
        Extract resource requirement estimates for a given set of workflow IDs.

        Parameters
        ----------
        resource_requirements : dict of int to dict
            Full resource requirements mapping.
        widxs : list of int
            Workflow IDs for which estimates are needed, in the desired order.

        Returns
        -------
        dict of str to list of float
            A dictionary with keys ``"estimated_walltime"``,
            ``"estimated_cpus"``, and ``"estimated_memory"``, each mapping to
            a list aligned with ``widxs``.
        """
        estimated_walltime = []
        estimated_cpus = []
        estimated_memory = []

        for widx in widxs:
            estimated_walltime.append(resource_requirements[widx]["req_walltime"])
            estimated_cpus.append(resource_requirements[widx]["req_cpus"])
            estimated_memory.append(resource_requirements[widx]["req_memory"])
        return {"estimated_walltime": estimated_walltime,
                "estimated_cpus": estimated_cpus,
                "estimated_memory": estimated_memory}

    def _get_sorted_workflow_indices(self, estimated_walltime: List[float]) -> List[int]:
        """
        Return workflow indices sorted by estimated walltime in descending order.

        HEFT schedules the longest task first to minimise the critical path.

        Parameters
        ----------
        estimated_walltime : list of float
            Estimated walltimes for the workflows in the current level.

        Returns
        -------
        list of int
            Indices into ``estimated_walltime`` sorted from longest to
            shortest walltime.
        """
        return [
            idx for idx, _ in sorted(
                enumerate(estimated_walltime),
                key=lambda x: x[1],
                reverse=True
            )
        ]

    def _initialize_resource_free_times(
        self, resources: range, start_time: float | int | list | np.ndarray
    ) -> np.ndarray:
        """
        Initialise an array tracking when each core becomes available.

        Parameters
        ----------
        resources : range
            Range of available core indices; its length determines the array size.
        start_time : float, int, list, or numpy.ndarray
            Initial availability time(s). A scalar is broadcast to all cores;
            an array or list is used directly.

        Returns
        -------
        numpy.ndarray
            1-D float array of length ``len(resources)`` with initial
            availability times.
        """
        if isinstance(start_time, (np.ndarray, list)):
            return np.array(start_time)
        elif isinstance(start_time, (float, int)):
            return np.array([start_time] * len(resources))
        else:
            return np.array([0.0] * len(resources))

    def _find_best_resource_slot(
        self,
        workflow_idx: int,
        resource_requirements: Dict[str, List[float]],
        resources: range,
        resource_free: np.ndarray,
        earlier_start: float
    ) -> Tuple[int, float]:
        """
        Find the core slot that yields the earliest finish time for a workflow.

        Slides a window of width ``req_cpus`` across the core array, computes
        the earliest feasible start time (respecting both core availability and
        dependency constraints), checks the available memory, and returns the
        slot with the minimum end time.

        Parameters
        ----------
        workflow_idx : int
            Index of the workflow within the current ``resource_requirements``
            lists.
        resource_requirements : dict of str to list of float
            Dictionary with ``"estimated_walltime"``, ``"estimated_cpus"``, and
            ``"estimated_memory"`` lists aligned to the current scheduling level.
        resources : range
            Available core range.
        resource_free : numpy.ndarray
            Per-core availability times (updated externally after each scheduling
            decision).
        earlier_start : float
            Minimum start time imposed by data dependencies.

        Returns
        -------
        tuple of (int, float)
            A 2-tuple ``(best_core_idx, actual_start_time)`` where
            ``best_core_idx`` is the starting index of the best core window
            and ``actual_start_time`` is the earliest feasible start within
            that window.
        """
        walltime = resource_requirements["estimated_walltime"][workflow_idx]
        memory_required = resource_requirements["estimated_memory"][workflow_idx]
        cpus_required = resource_requirements["estimated_cpus"][workflow_idx]

        min_end_time = float("inf")
        best_core_idx = 0
        core_idx = 0

        while (core_idx + cpus_required) <= len(resources):
            core_slice = slice(core_idx, core_idx + cpus_required)
            start_time_candidate = max(resource_free[core_slice].max(), earlier_start)
            end_time_candidate = start_time_candidate + walltime

            free_memory = self._get_free_memory(start_time_candidate, len(resources) / self._resources.cores_per_node)

            if free_memory >= memory_required:
                self._logger.debug(
                    f"Workflow {workflow_idx}: candidate finish time {end_time_candidate}"
                )
                if end_time_candidate < min_end_time:
                    min_end_time = end_time_candidate
                    best_core_idx = core_idx
                self._logger.debug(
                    f"Workflow {workflow_idx}: minimum finish time {min_end_time}"
                )
            else:
                self._logger.debug(
                    f"Insufficient memory: {free_memory} MB available, {memory_required} MB required"
                )

            core_idx += cpus_required

        return best_core_idx, min_end_time - walltime

    def _calculate_plan(
        self,
        campaign: DAG | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: float = 0.0,
    ) -> Tuple[List[PlanEntry], nx.DiGraph]:
        """
        Core HEFT scheduling algorithm implementation.

        Iterates over topological workflow levels, sorts each level by
        descending estimated walltime, and calls
        :meth:`_find_best_resource_slot` for each workflow to assign it a
        core window and time interval. Updates per-core availability times
        after each assignment.

        Parameters
        ----------
        campaign : DAG or None, optional
            The workflow DAG. Falls back to ``self._campaign.workflows``
            if ``None``.
        resources : range or None, optional
            Available core range. Falls back to all cores on the resource
            if ``None``.
        resource_requirements : dict of int to dict, or None, optional
            Per-workflow resource requirements. Falls back to
            ``self._resource_requirements`` if ``None``.
        start_time : float, optional
            Initial availability time for all cores (in minutes). Defaults to
            ``0.0``. May also be an array of per-core times when called from
            :meth:`replan`.

        Returns
        -------
        tuple of (list of PlanEntry, networkx.DiGraph)
            The scheduled plan entries (sorted by workflow ID) and the
            resource-ordering dependency graph.
        """
        workflow_levels = campaign.levels if campaign else self._campaign.workflows.levels

        cores = (
            resources
            if resources
            else range(self._resources.nodes * self._resources.cores_per_node)
        )
        resource_requirements = resource_requirements if resource_requirements else self._resource_requirements
        # Reset plan for fresh scheduling
        self._plan: List[PlanEntry] = []

        # Track when each core becomes available
        resource_free = self._initialize_resource_free_times(cores, start_time)

        for workflows in workflow_levels:
            requirements = self._initialize_resource_estimates(resource_requirements=resource_requirements,
                                                widxs=[w.id for w in workflows])

            # Sort workflows by execution time (longest first)
            sorted_indices = self._get_sorted_workflow_indices(estimated_walltime=requirements["estimated_walltime"])

            # Schedule each workflow
            for workflow_idx in sorted_indices:
                workflow = workflows[workflow_idx]
                earliest_start = 0
                if workflow.depends:
                    for entry in self._plan:
                        if entry.workflow.name in workflow.depends:
                            earliest_start = max(earliest_start, entry.end_time)
                best_core_idx, start_time_actual = self._find_best_resource_slot(
                    workflow_idx, requirements, cores, resource_free, earlier_start=earliest_start
                )

                walltime = requirements["estimated_walltime"][workflow_idx]
                memory_required = requirements["estimated_memory"][workflow_idx]
                cpus_required = requirements["estimated_cpus"][workflow_idx]
                core_slice = slice(best_core_idx, best_core_idx + cpus_required)

                # Create plan entry
                plan_entry = PlanEntry(
                    workflow=workflows[workflow_idx],
                    cores=cores[core_slice],
                    memory=memory_required,
                    start_time=start_time_actual,
                    end_time=start_time_actual + walltime
                )
                self._plan.append(plan_entry)

                # Update resource availability
                resource_free[core_slice] = start_time_actual + walltime

        # Build dependency graph
        plan_graph = self._get_plan_graph(self._plan, cores)

        # Sort plan by workflow ID for consistent ordering
        self._plan = sorted(self._plan, key=lambda entry: entry.workflow.id)
        self._logger.debug("Potential plan %s", self._plan)

        return self._plan, plan_graph

    def replan(
        self,
        campaign: DAG | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: float = 0.0,
    ) -> Tuple[List[PlanEntry], nx.DiGraph]:
        """
        Recalculate the execution plan with updated parameters.

        If all three update parameters are provided, delegates to
        :meth:`_calculate_plan`. Otherwise returns the existing plan unchanged.

        Parameters
        ----------
        campaign : DAG or None, optional
            Updated campaign DAG.
        resources : range or None, optional
            Updated core range.
        resource_requirements : dict of int to dict, or None, optional
            Updated per-workflow resource requirements.
        start_time : float, optional
            New start time or per-core availability times. Defaults to ``0.0``.

        Returns
        -------
        tuple of (list of PlanEntry, networkx.DiGraph)
            The updated (or unchanged) plan entries and dependency graph.
        """
        if campaign and resources and resource_requirements:
            self._logger.debug("Replanning with updated parameters")
            return self._calculate_plan(
                campaign=campaign,
                resources=resources,
                resource_requirements=resource_requirements,
                start_time=start_time,
            )
        else:
            self._logger.debug("Nothing to replan - missing required parameters")
            return self._plan, self._get_plan_graph(self._plan, resources or range(0))
