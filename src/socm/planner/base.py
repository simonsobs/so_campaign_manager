import os
from typing import Dict, List, Tuple

import networkx as nx
import radical.utils as ru

from ..core import DAG, Campaign, PlanEntry, PlanResult, Resource


class Planner(object):
    """
    Abstract base class for campaign execution planners.

    A planner receives the campaign workflow DAG, the available HPC resource,
    and per-workflow resource-requirement estimates, then computes a scheduling
    plan. The plan maps each workflow to a core range, a memory allocation, and
    a time window (start/end in minutes).

    Concrete subclasses must override :meth:`plan`. Optionally they may also
    override :meth:`replan` to support re-scheduling after workflow failures or
    completions.

    Parameters
    ----------
    campaign : Campaign or None, optional
        The campaign object containing the workflow DAG. May be supplied here
        for convenience or passed directly to :meth:`plan`.
    resources : Resource or None, optional
        The HPC resource description used for scheduling decisions.
    resource_requirements : dict of int to dict, or None, optional
        A mapping of workflow ID to resource requirement dictionaries
        containing ``req_cpus``, ``req_memory``, and ``req_walltime``.
    policy : str or None, optional
        Scheduling policy string (planner-specific interpretation).
    sid : str or None, optional
        Session ID used to namespace logger and profiler instances.
    objective : int or None, optional
        Campaign makespan objective in minutes.
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

        Subclasses must override this method. The base implementation always
        raises :class:`NotImplementedError`.

        Parameters
        ----------
        campaign : DAG or None, optional
            The campaign DAG containing workflows and dependency edges.
        resources : range or None, optional
            The available core range for scheduling.
        resource_requirements : dict of int to dict, or None, optional
            Per-workflow resource requirements keyed by workflow ID, each
            containing ``req_cpus``, ``req_memory``, and ``req_walltime``.
        start_time : int, optional
            Start time offset (in minutes) for the scheduled plan.
        **kargs
            Additional keyword arguments for subclass implementations.

        Returns
        -------
        PlanResult
            The complete planning result containing the selected QoS policy,
            the total core count, and the list of execution batches.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
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
        Recalculate the execution plan, typically after a workflow completion or failure.

        Subclasses may override this method to support dynamic re-scheduling.
        The base implementation always raises :class:`NotImplementedError`.

        Parameters
        ----------
        campaign : DAG or None, optional
            The updated campaign DAG.
        resources : range or None, optional
            The available core range for scheduling.
        resource_requirements : dict of int to dict, or None, optional
            Updated per-workflow resource requirements keyed by workflow ID.
        start_time : int, optional
            Start time offset (in minutes) for the replanned schedule.

        Returns
        -------
        tuple of (list of PlanEntry, networkx.DiGraph)
            The updated plan entries and the corresponding dependency graph.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("Replan method is not implemented")
