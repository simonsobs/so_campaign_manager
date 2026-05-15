from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

from ..core import DAG, Batch, Campaign, PlanEntry, PlanResult, QosPolicy, Resource
from .base import Planner


class HeftPlanner(Planner):
    """Campaign planner using Heterogeneous Earliest Finish Time (HEFT) algorithm.

    HEFT is a list scheduling algorithm that assigns tasks to processors to minimize
    the overall completion time, considering both computation and communication costs.

    Reference:
        Topcuoglu, H., Hariri, S., & Wu, M. Y. (2002). Performance-effective and
        low-complexity task scheduling for heterogeneous computing.
        IEEE Transactions on Parallel and Distributed Systems, 13(3), 260-274.

    Attributes:
        _estimated_walltime: List of estimated execution times (walltime) for each workflow
        _estimated_cpus: List of estimated CPU requirements for each workflow
        _estimated_memory: List of estimated memory requirements for each workflow
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
        """Calculate available memory at a given time.

        Args:
            start_time: Time point to check memory availability
            num_nodes: The total number of nodes used

        Returns:
            Available memory in MB
        """
        total_memory = num_nodes * self._resources.memory_per_node
        used_memory = sum(
            entry.memory
            for entry in self._plan
            if entry.start_time <= start_time < entry.end_time
        )
        return total_memory - used_memory

    def _get_max_ncores(self, resource_requirements: Dict[int, Dict[str, float]]) -> int:
        """Get the maximum number of cores required by any single workflow."""
        return max(values["req_cpus"] for values in resource_requirements.values())

    def _find_suitable_qos_policies(self, requested_cores: int) -> QosPolicy:
        """Find QoS policies that can accommodate the campaign deadline."""
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
        """Binary search for minimum resources that satisfy the deadline.

        Returns:
            Tuple of (ncores, plan, graph) if successful, None otherwise.
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
        """Extract the subgraph for a batch, dropping cross-batch edges.

        Args:
            graph: Full plan dependency graph
            workflow_ids: Workflow IDs belonging to this batch

        Returns:
            DiGraph containing only intra-batch nodes and edges
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
        """Split a plan into batches where each batch fits within max_walltime.

        Entries are assigned to batches greedily by end_time. A new batch starts
        when the next entry's end_time would exceed the current batch window.
        Cross-batch dependency edges are dropped because sequential batch execution
        guarantees ordering.

        Args:
            plan: Full list of plan entries (will be sorted by end_time internally)
            graph: Full plan dependency graph
            max_walltime: Maximum duration (in plan time units) per batch

        Returns:
            List of Batch objects
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
        """Find optimal QoS and resource allocation for the campaign.

        Attempts a single-pilot fit first. If no single QoS policy can accommodate
        both the required cores and the campaign deadline, the plan is split into
        sequential batches using the highest-walltime QoS that covers the core count.

        Returns:
            PlanResult with qos, ncores, and one or more batches.
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
        max_walltime = best_qos.max_walltime

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
        """Build dependency graph from the execution plan.

        Args:
            plan: Execution plan with scheduled workflows
            resources: Available resource cores

        Returns:
            Directed acyclic graph representing workflow dependencies
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
        """Plan campaign execution with resource allocation.

        In batch mode, uses the requested resources directly.
        In remote mode, performs QoS selection and binary search to find the minimum
        resources that satisfy the campaign deadline, splitting into multiple batches
        if no single QoS policy covers both cores and deadline.

        Parameters
        ----------
        campaign : DAG | None
            The campaign DAG to plan
        resource_requirements : Dict[int, Dict[str, float]] | None
            Per-workflow resource requirements keyed by workflow ID.
        execution_schema : str | None
            'batch' for fixed resources, 'remote' for optimized allocation
        requested_resources : int | None
            Number of cores

        Returns
        -------
        PlanResult
            Contains the selected QoS policy (None for batch mode), core count,
            and one or more Batch objects representing pilot submissions.
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
        """Plan execution for batch mode with fixed resources (single batch, no QoS)."""
        plan, plan_graph = self._calculate_plan(
            campaign=campaign,
            resources=range(requested_resources),
            resource_requirements=resource_requirements
        )
        self._logger.info(f"Plan to execute {plan} with {requested_resources} cores")
        return PlanResult(qos=None, ncores=requested_resources, batches=[Batch(plan=plan, graph=plan_graph)])

    def _initialize_resource_estimates(self, resource_requirements: Dict[int, Dict[str, float]], widxs: List[int]
    ) -> Dict[str, List[float]]:
        """Extract and store resource requirement estimates from workflows."""
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
        """Get workflow indices sorted by execution time (longest first).

        Returns:
            List of workflow indices in descending order of execution time
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
        """Initialize array tracking when each resource becomes available.

        Args:
            resources: Range of available resource cores
            start_time: Initial availability time(s)

        Returns:
            Array of availability times for each core
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
        """Find the best resource slot for a workflow.

        Args:
            workflow_idx: Index of the workflow to schedule
            resource_requirements: Dict of estimated resource lists
            resources: Available resource cores
            resource_free: Array tracking when each core becomes available
            earlier_start: Earliest allowed start time (from dependency constraints)

        Returns:
            Tuple of (best_core_index, earliest_start_time)
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
        """Implement the core HEFT scheduling algorithm.

        Args:
            campaign: DAG of workflows to schedule
            resources: Available resource cores
            resource_requirements: Resource needs for each workflow
            start_time: Initial time or per-core availability times

        Returns:
            Tuple of (execution_plan, dependency_graph)
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
        """Recalculate the execution plan with updated parameters.

        Args:
            campaign: Updated list of workflows
            resources: Updated resource allocation
            resource_requirements: Updated resource requirements
            start_time: New start time or per-core availability

        Returns:
            Tuple of (execution_plan, dependency_graph)
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
