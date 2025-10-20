from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

from ..core import Campaign, QosPolicy, Resource, Workflow
from .base import PlanEntry, Planner


class HeftPlanner(Planner):
    """Campaign planner using Heterogeneous Earliest Finish Time (HEFT) algorithm.

    HEFT is a list scheduling algorithm that assigns tasks to processors to minimize
    the overall completion time, considering both computation and communication costs.

    Reference:
        Topcuoglu, H., Hariri, S., & Wu, M. Y. (2002). Performance-effective and
        low-complexity task scheduling for heterogeneous computing.
        IEEE Transactions on Parallel and Distributed Systems, 13(3), 260-274.

    Attributes:
        _est_tx: List of estimated execution times (walltime) for each workflow
        _est_cpus: List of estimated CPU requirements for each workflow
        _est_memory: List of estimated memory requirements for each workflow
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
        self._est_tx: List[float] = []
        self._est_cpus: List[int] = []
        self._est_memory: List[float] = []

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

    def _find_suitable_qos_policies(self, cores:int) -> QosPolicy:
        """Find QoS policies that can accommodate the campaign deadline."""
        suitable_qos = self._resources.fits_in_qos(self._objective, cores)
        if not suitable_qos:
            raise ValueError(f"No QoS policy can accommodate deadline of {self._objective} minutes")

        return suitable_qos

    def _binary_search_resources(
        self,
        campaign: List[Workflow],
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

    def _plan_with_qos_optimization(
        self,
        campaign: List[Workflow],
        resource_requirements: Dict[int, Dict[str, float]]
    ) -> Tuple[List[PlanEntry], nx.DiGraph, str, int]:
        """Find optimal QoS and resource allocation for the campaign.

        Returns:
            Tuple of (plan, graph, qos_name, ncores).
        """
        max_workflow_resources = self._get_max_ncores(resource_requirements)
        qos_candidate = self._find_suitable_qos_policies(cores=max_workflow_resources)

        # Try each suitable QoS until we find one that works

        # Start with min(2x max workflow resources, QoS max cores)
        upper_bound = min(max_workflow_resources * 2, qos_candidate.max_cores)
        lower_bound = max_workflow_resources

        result = self._binary_search_resources(
            campaign, resource_requirements, lower_bound, upper_bound
        )

        if result is not None:
            ncores, plan, plan_graph = result
            return plan, plan_graph, qos_candidate.name, ncores

        raise ValueError(
            f"Could not find resource allocation that meets deadline of {self._objective} minutes"
        )

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
        campaign: List[Workflow] | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        execution_schema: str | None = None,
        requested_resources: int | None = None
    ) -> Tuple[List[PlanEntry], nx.DiGraph, QosPolicy | None, int]:
        """Plan campaign execution with resource allocation.

        In batch mode, uses the requested resources directly.
        In remote mode, performs QoS selection and binary search to find the minimum
        resources that satisfy the campaign deadline.

        Parameters
        ----------
        campaign : List[Workflow] | None
            The campaign workflows to plan
        resource_requirements : Dict[int, Dict[str, float]] | None
            Resource requirements for each workflow
        execution_schema : str | None
            'batch' for fixed resources, 'remote' for optimized allocation
        requested_resources : int | None
            Number of cores (batch mode only)

        Returns
        -------
        Tuple[plan, graph, qos, ncores]
            - plan: List of PlanEntry tuples
            - graph: DAG representation of the campaign
            - qos: QoS policy name (None for batch mode)
            - ncores: Number of cores allocated
        """
        if execution_schema == "batch":
            return self._plan_batch_mode(campaign, resource_requirements, requested_resources)
        else:
            return self._plan_with_qos_optimization(campaign, resource_requirements)

    def _plan_batch_mode(
        self,
        campaign: List[Workflow],
        resource_requirements: Dict[int, Dict[str, float]],
        requested_resources: int
    ) -> Tuple[List[PlanEntry], nx.DiGraph, None, int]:
        """Plan execution for batch mode with fixed resources."""
        plan, plan_graph = self._calculate_plan(
            campaign=campaign,
            resources=range(requested_resources),
            resource_requirements=resource_requirements
        )
        return plan, plan_graph, None, requested_resources

    def _initialize_resource_estimates(
        self, resource_requirements: Dict[int, Dict[str, float]]
    ) -> None:
        """Extract and store resource requirement estimates from workflows."""
        self._est_tx = []
        self._est_cpus = []
        self._est_memory = []

        for resource_req in resource_requirements.values():
            self._est_tx.append(resource_req["req_walltime"])
            self._est_cpus.append(resource_req["req_cpus"])
            self._est_memory.append(resource_req["req_memory"])

    def _get_sorted_workflow_indices(self) -> List[int]:
        """Get workflow indices sorted by execution time (longest first).

        Returns:
            List of workflow indices in descending order of execution time
        """
        return [
            idx for idx, _ in sorted(
                enumerate(self._est_tx),
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
        resources: range,
        resource_free: np.ndarray
    ) -> Tuple[int, float]:
        """Find the best resource slot for a workflow.

        Args:
            workflow_idx: Index of the workflow to schedule
            resources: Available resource cores
            resource_free: Array tracking when each core becomes available

        Returns:
            Tuple of (best_core_index, earliest_start_time)
        """
        walltime = self._est_tx[workflow_idx]
        memory_required = self._est_memory[workflow_idx]
        cpus_required = self._est_cpus[workflow_idx]

        min_end_time = float("inf")
        best_core_idx = 0
        core_idx = 0

        while (core_idx + cpus_required) <= len(resources):
            core_slice = slice(core_idx, core_idx + cpus_required)
            start_time_candidate = resource_free[core_slice].max()
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
        campaign: List[Workflow] | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: float = 0.0,
    ) -> Tuple[List[PlanEntry], nx.DiGraph]:
        """Implement the core HEFT scheduling algorithm.

        Args:
            campaign: List of workflows to schedule
            resources: Available resource cores
            resource_requirements: Resource needs for each workflow
            start_time: Initial time or per-core availability times

        Returns:
            Tuple of (execution_plan, dependency_graph)
        """
        # Use provided parameters or fall back to instance attributes
        workflows = campaign if campaign else self._campaign
        cores = (
            resources
            if resources
            else range(self._resources.nodes * self._resources.cores_per_node)
        )
        requirements = resource_requirements if resource_requirements else self._resource_requirements

        # Initialize estimation tables
        self._initialize_resource_estimates(requirements)

        # Reset plan for fresh scheduling
        self._plan: List[PlanEntry] = []

        # Sort workflows by execution time (longest first)
        sorted_indices = self._get_sorted_workflow_indices()

        # Track when each core becomes available
        resource_free = self._initialize_resource_free_times(cores, start_time)

        # Schedule each workflow
        for workflow_idx in sorted_indices:
            best_core_idx, start_time_actual = self._find_best_resource_slot(
                workflow_idx, cores, resource_free
            )

            cpus_required = self._est_cpus[workflow_idx]
            walltime = self._est_tx[workflow_idx]
            memory_required = self._est_memory[workflow_idx]
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
        self._logger.info("Sorted plan %s", self._plan)

        return self._plan, plan_graph

    def replan(
        self,
        campaign: List[Workflow] | None = None,
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
