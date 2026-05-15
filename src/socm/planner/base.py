import os
from typing import Dict, List

import radical.utils as ru

from ..core import DAG, Campaign, PlanEntry, PlanResult, Resource


class Planner(object):
    """
    Base planner that computes an execution plan for a campaign.

    The planner receives a campaign, a set of resources, and execution time
    estimates for each workflow, then calculates a scheduling plan. The plan
    is a list of PlanEntry tuples mapping each workflow to a core range,
    memory allocation, and time window.

    Each planning subclass must implement the ``plan`` method. Subclasses
    can override the basic plan with additional scheduling logic.
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
        self._campaign = campaign
        self._resources = resources
        self._resource_requirements = resource_requirements
        self._policy = policy
        self._objective = objective
        self._plan: List[PlanEntry] = []
        self._uid = ru.generate_id("planner.%(counter)04d", mode=ru.ID_CUSTOM, ns=sid)
        sid = sid if sid is not None else ru.generate_id("planner.%(counter)04d", mode=ru.ID_CUSTOM)
        path = os.getcwd() + "/" + sid
        self._logger = ru.Logger(name=self._uid, level="DEBUG", path=path)

    def plan(
        self,
        campaign: DAG | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: int = 0,
        **kargs,
    ) -> PlanResult:
        """
        Calculate an execution plan for the given campaign and resources.

        Parameters
        ----------
        campaign : DAG or None, optional
            The campaign DAG containing workflows and dependencies.
        resources : range or None, optional
            The available core range for scheduling.
        resource_requirements : dict or None, optional
            A mapping of workflow IDs to their resource requirements.
        start_time : int, optional
            The start time offset for the plan.
        **kargs
            Additional keyword arguments for subclass implementations.

        Returns
        -------
        PlanResult
            The complete planning result containing QoS policy, core count, and execution batches.
        """
        raise NotImplementedError("Plan method is not implemented")

    def replan(
        self,
        campaign: DAG | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: int = 0,
    ) -> PlanResult:
        """
        Recalculate the execution plan, typically after workflow completion.

        Parameters
        ----------
        campaign : DAG or None, optional
            The updated campaign DAG.
        resources : range or None, optional
            The available core range for scheduling.
        resource_requirements : dict or None, optional
            A mapping of workflow IDs to their resource requirements.
        start_time : int, optional
            The start time offset for the replan.

        Returns
        -------
        PlanResult
            The complete planning result containing QoS policy, core count, and execution batches.
        """
        raise NotImplementedError("Replan method is not implemented")
