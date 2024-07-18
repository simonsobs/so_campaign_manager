import numpy as np
import networkx as nx

from line_profiler import profile
from typing import List, Tuple, Dict
from sortedcontainers import SortedDict
from .base import Planner

from ..core import Workflow, Campaign, Resource


class HeftPlanner(Planner):
    """
    This class implemements a campaign planner based on Heterogeneous Earliest
    Finish Time (HEFT) scheduling algorithm.

    For reference:
    H. Topcuoglu, S. Hariri, and Min-You Wu. Performance-effective and
    low-complexity task scheduling for heterogeneous computing.
    IEEE Transactions on Parallel and Distributed Systems, March 2002.

    Constractor parameters:
    campaign: A list of workflows
    resources: A list of resources, whose performance is given in operations per second
    num_oper: The number of operations each workflow will execute

    The class implements a plan method that return a plan, a list of tuples.

    Each tuple will have the workflow, selected resource, starting time and
    estimated finish time.
    """

    def __init__(
        self,
        campaign: Campaign,
        resources: Resource,
        resource_requirements: Dict[int, Dict[str, float]],
        policy: str,
        sid: str = None,
    ):

        super(HeftPlanner, self).__init__(
            campaign=campaign,
            resources=resources,
            resource_requirements=resource_requirements,
            sid=sid,
            policy=policy,
        )

        # Calculate the estimated execution time of each workflow on to each
        # resource. This table will be used to calculate the plan.
        # est_tx holds this table. The index of the table is
        # <workflow_idx, resource_idx>, and each entry is the estimated
        # execution time of a workflow on a resource.
        # TODO: not all workflows can run in a resource
        self._est_tx = list()
        self._est_cpus = list()
        self._est_memory = list()
        for _, resource_req in resource_requirements.items():
            self._est_tx.append(resource_req["req_walltime"])
            self._est_cpus.append(resource_req["req_cpus"])

    def _get_free_memory(self, start_time: int):

        free_memory = self._resources.nodes * self._resources.memory_per_node
        for p in self._plan:
            if p[-2] <= start_time and p[-1] > start_time:
                free_memory -= p[-3]

        return free_memory

    def _get_plan_graph(
        self, plan: List[Tuple[Workflow, range, float, float, float]], resources: range
    ) -> nx.DiGraph:

        self._logger.debug("Create resource dependency DAG")
        graph = nx.DiGraph()
        deps = {}
        for i in range(len(resources)):
            deps[i] = None

        for workflow, cores, _, _, _ in plan:
            previous_tasks = set()
            for i in cores:
                if deps[i] is not None:
                    previous_tasks.add(deps[i])
                deps[i] = workflow.id

            if len(previous_tasks) == 0:
                graph.add_node(workflow.id)
            else:
                for n in previous_tasks:
                    graph.add_edges_from([(n, workflow.id)])
        self._logger.info(f"Calculated graph {graph}")

        return graph

    @profile
    def plan(
        self,
        campaign: List[Workflow] = None,
        resources: range = None,
        resource_requirements: Dict[int, Dict[str, float]] = None,
        start_time: int = 0,
    ) -> Tuple[List[Tuple[Workflow, range, float, float]], nx.DiGraph]:
        """
        This method implements the basic HEFT algorithm. It returns a list of tuples
        Each tuple contains: Workflow ID, Resource ID, Start Time, End Time.

        The plan method takes as input a campaign, resources and num_oper in case
        any of these has changed. They default to `None`

        *Returns:*
            list(tuples), DAG
        """

        tmp_cmp = campaign if campaign else self._campaign
        tmp_res = (
            resources
            if resources
            else range(self._resources.nodes * self._resources.cores_per_node)
        )
        tmp_nop = (
            resource_requirements
            if resource_requirements
            else self._resource_requirements
        )

        self._est_tx = list()
        self._est_cpus = list()
        for _, resource_req in tmp_nop.items():
            self._est_tx.append(resource_req["req_walltime"])
            self._est_cpus.append(resource_req["req_cpus"])
            self._est_memory.append(resource_req["req_memory"])

        # Reset the plan in case of a recall
        self._plan = list()

        # Get the indices of the sorted list.
        av_est_idx_sorted = [
            i[0]
            for i in sorted(enumerate(self._est_tx), key=lambda x: x[1], reverse=True)
        ]

        # This list tracks when a resource whould be available.
        if isinstance(start_time, np.ndarray) or isinstance(start_time, list):
            resource_free = np.array(start_time)
        elif isinstance(start_time, float) or isinstance(start_time, int):
            resource_free = np.array([start_time] * len(tmp_res))
        else:
            resource_free = np.array([0] * len(tmp_res))

        for sorted_idx in av_est_idx_sorted:
            wf_est_tx = self._est_tx[sorted_idx]
            wf_mem_rq = self._est_memory[sorted_idx]
            wf_est_cpus = self._est_cpus[sorted_idx]
            min_end_time = float("inf")
            i = 0
            while (i + wf_est_cpus) < len(tmp_res):
                # for i in range(0, len(tmp_res), wf_est_cpus):
                tmp_str_time = resource_free[i : i + wf_est_cpus]
                tmp_end_time = tmp_str_time + wf_est_tx
                free_memory = self._get_free_memory(tmp_str_time.max())
                if free_memory >= wf_mem_rq:
                    self._logger.debug(
                        f"Estimated Finish time {sorted_idx}: {tmp_end_time}"
                    )
                    if (tmp_end_time < min_end_time).all():
                        min_end_time = tmp_end_time.max()
                        tmp_min_idx = i
                    self._logger.debug(
                        f"Minimum Finish Time {sorted_idx}: {min_end_time}"
                    )
                else:
                    self._logger.debug(f"Not enough memory {free_memory}, {wf_mem_rq}")
                i += wf_est_cpus
            start_times = resource_free[tmp_min_idx : tmp_min_idx + wf_est_cpus].max()
            self._plan.append(
                (
                    tmp_cmp[sorted_idx],
                    tmp_res[tmp_min_idx : tmp_min_idx + wf_est_cpus],
                    wf_mem_rq,
                    start_times,
                    start_times + wf_est_tx,
                )
            )
            resource_free[tmp_min_idx : tmp_min_idx + wf_est_cpus] = (
                start_times + wf_est_tx
            )
        plan_graph = self._get_plan_graph(self._plan, tmp_res)
        # self._logger.info("Derived plan %s", self._plan)
        self._plan = sorted(
            [place for place in self._plan], key=lambda place: place[0].id
        )
        self._logger.info("Sorted plan %s", self._plan)
        return self._plan, plan_graph

    def replan(
        self,
        campaign: List[Workflow] = None,
        resources: range = None,
        resource_requirements: Dict[int, Dict[str, float]] = None,
        start_time: int = 0,
    ) -> Tuple[List[Tuple[Workflow, range, float, float]], nx.DiGraph]:
        """
        The planning method
        """
        if campaign and resources and resource_requirements:
            self._logger.debug("Replanning")
            self._plan, plan_graph = self.plan(
                campaign=campaign,
                resources=resources,
                resource_requirements=resource_requirements,
                start_time=start_time,
            )
        else:
            self._logger.debug("Nothing to plan for")

        return self._plan, plan_graph
