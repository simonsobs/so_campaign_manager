"""
Author: Ioannis Paraskevakos
License: MIT
Copyright: 2018-2019
"""
import numpy as np
from .base import Planner


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

    def __init__(self, campaign, resources, resource_requirements, policy, sid=None):

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
        for _, resource_req in resource_requirements.items():
            self._est_tx.append(resource_req["req_walltime"])
            self._est_cpus.append(resource_req["req_cpus"])

    def plan(
        self,
        campaign=None,
        resources=None,
        resource_requirements=None,
        start_time=None,
        **kargs,
    ):
        """
        This method implements the basic HEFT algorithm. It returns a list of tuples
        Each tuple contains: Workflow ID, Resource ID, Start Time, End Time.

        The plan method takes as input a campaign, resources and num_oper in case
        any of these has changed. They default to `None`

        *Returns:*
            list(tuples)
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
        res_perf = [1] * self._resources.nodes * self._resources.cores_per_node
        # print(res_perf)
        self._est_tx = list()
        self._est_cpus = list()
        for _, resource_req in tmp_nop.items():
            self._est_tx.append(resource_req["req_walltime"])
            self._est_cpus.append(resource_req["req_cpus"])

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
            wf_est_cpus = self._est_cpus[sorted_idx]
            min_end_time = float("inf")
            for i in range(0, len(tmp_res), wf_est_cpus):
                tmp_str_time = resource_free[i : i + wf_est_cpus]
                tmp_end_time = tmp_str_time + wf_est_tx
                if tmp_end_time.ptp() == 0 and (tmp_end_time < min_end_time).all():
                    min_end_time = tmp_end_time
                    tmp_min_idx = i
            start_times = resource_free[tmp_min_idx : tmp_min_idx + wf_est_cpus].copy()
            self._plan.append(
                (
                    tmp_cmp[sorted_idx],
                    tmp_res[tmp_min_idx : tmp_min_idx + wf_est_cpus],
                    start_times,
                    start_times + wf_est_tx,
                )
            )
            resource_free[tmp_min_idx : tmp_min_idx + wf_est_cpus] = (
                resource_free[tmp_min_idx : tmp_min_idx + wf_est_cpus] + wf_est_tx
            )

        self._logger.info("Derived plan %s", self._plan)
        return self._plan

    def replan(self, campaign=None, resources=None, num_oper=None, start_time=0):
        """
        The planning method
        """
        if campaign and resources and num_oper:
            self._logger.debug("Replanning")
            self._plan = self.plan(
                campaign=campaign,
                resources=resources,
                num_oper=num_oper,
                start_time=start_time,
            )
        else:
            self._logger.debug("Nothing to plan for")

        return self._plan
