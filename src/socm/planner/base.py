import os
from typing import Dict, List, NamedTuple, Tuple

import networkx as nx
import radical.utils as ru

from ..core import DAG, Campaign, Resource, Workflow


class PlanEntry(NamedTuple):
    """Represents a scheduled workflow in the execution plan."""
    workflow: Workflow
    cores: range
    memory: float
    start_time: float
    end_time: float

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
    ) -> Tuple[List[PlanEntry], nx.DiGraph]:
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
        tuple[list[PlanEntry], nx.DiGraph]
            A tuple of (plan_entries, dependency_graph) where plan_entries
            is a list of PlanEntry named tuples and dependency_graph is a
            NetworkX DiGraph.
        """

        raise NotImplementedError("Plan method is not implemented")

    def replan(
        self,
        campaign: DAG | None = None,
        resources: range | None = None,
        resource_requirements: Dict[int, Dict[str, float]] | None = None,
        start_time: int = 0,
    ) -> Tuple[List[PlanEntry], nx.DiGraph]:
        """
        Recalculate the execution plan, typically after workflow completion.

        Delegates to ``plan()`` if all required arguments are provided.

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
        tuple
            A tuple of (plan_entries, dependency_graph).
        """
        if campaign and resources and resource_requirements:
            self._logger.debug("Replanning")
            self._plan = self.plan(
                campaign=campaign,
                resources=resources,
                resource_requirements=resource_requirements,
                start_time=start_time,
            )
        else:
            self._logger.debug("Nothing to plan for")

        return self._plan
