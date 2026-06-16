import os
from typing import Dict, List

import radical.utils as ru

from socm.core import Resource, Workflow
from socm.utils.states import States


class Enactor(object):
    """
    Abstract base class for campaign workflow enactors.

    An enactor is responsible for submitting workflows to an HPC resource and
    monitoring their execution. Concrete subclasses implement the execution
    back-end (e.g. RADICAL-Pilot, dry-run) by overriding the abstract methods.

    State updates are delivered to registered callbacks. Each callback is
    invoked with ``workflow_ids``, ``new_state``, and ``step_ids`` keyword
    arguments whenever a workflow changes state.

    Parameters
    ----------
    sid : str or None, optional
        Session ID used to construct namespaced logger and profiler file paths.

    Attributes
    ----------
    _worflows : list
        List of workflow IDs that have been submitted for execution.
    _execution_status : dict
        Mapping of workflow ID to a status dictionary containing at minimum:

        * ``"state"`` — current :class:`~socm.utils.states.States` value.
        * ``"endpoint"`` — back-end task object or ``None``.
        * ``"exec_thread"`` — execution thread or ``None``.
        * ``"start_time"`` — submission timestamp.
        * ``"end_time"`` — completion timestamp or ``None``.
    _logger : radical.utils.Logger
        RADICAL-Utils logger instance.
    _prof : radical.utils.Profiler
        RADICAL-Utils profiler instance.
    """

    def __init__(self, sid=None):

        self._worflows = list()  # A list of workflows IDs
        # This will a hash table of workflows. The table will include the
        # following:
        # 'workflowsID': {'state': The state of the workflow based on the WFM,
        #                 'endpoint': Process ID or object to WMF for the specific
        #                             workflow,
        #                 'start_time': Epoch of when the workflow is submitted
        #                               to the WMF,
        #                 'end_time': Epoch of when the workflow finished.}
        self._execution_status = dict()  # This will create a hash table of workflows

        self._uid = ru.generate_id("enactor.%(counter)04d", mode=ru.ID_CUSTOM, ns=sid)

        path = os.getcwd() + "/" + sid
        # print(path)
        name = self._uid

        self._logger = ru.Logger(name=self._uid, path=path, level="DEBUG")
        self._prof = ru.Profiler(name=name, path=path)

    def setup(self, resource: Resource, walltime: int, cores: int, execution_schema: str | None = None) -> None:
        """
        Set up the enactor with resource configuration for workflow execution.

        Must be called before :meth:`enact`. Concrete subclasses use this
        method to create pilot jobs or otherwise reserve HPC resources.

        Parameters
        ----------
        resource : Resource
            The HPC resource on which workflows will execute.
        walltime : int
            Maximum walltime in minutes for the pilot or allocation.
        cores : int
            Number of cores to request.
        execution_schema : str or None, optional
            Access schema (e.g. ``"batch"`` or ``"local"``). Interpretation is
            back-end specific.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("setup is not implemented")

    def enact(self, workflows: List[Workflow]) -> None:
        """
        Submit a list of workflows for execution.

        Must be overridden by concrete subclasses. Each workflow in the list
        should be submitted to the back-end and its initial state recorded in
        :attr:`_execution_status`.

        Parameters
        ----------
        workflows : list of Workflow
            Workflows to submit for execution.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("enact is not implemented")

    def _monitor(self):
        """
        Monitor the execution status of submitted workflows.

        Runs in a background thread in concrete implementations. Updates
        :attr:`_execution_status` and invokes registered state callbacks when
        workflows reach final states.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("_monitor is not implemented")

    def get_status(self, workflows: str | List[str] | None = None) -> Dict[str, States]:
        """
        Get the execution state of one or more workflows.

        Parameters
        ----------
        workflows : str, list of str, or None, optional
            A single workflow ID, a list of workflow IDs, or ``None`` to
            retrieve the state of every tracked workflow.

        Returns
        -------
        dict of str to States
            A mapping of workflow ID to its current :class:`~socm.utils.states.States` value.
        """

        status = dict()
        if workflows is None:
            for workflow in self._execution_status:
                status[workflow] = self._execution_status[workflow]["state"]
        elif isinstance(workflows, list):
            for workflow in workflows:
                status[workflow] = self._execution_status[workflow]["state"]
        else:
            status[workflows] = self._execution_status[workflows]["state"]

        return status

    def update_status_cb(self, workflow, new_state):
        """
        Update the execution state of a workflow via an external callback.

        Logs a warning if the workflow has not yet been submitted (i.e. is
        not present in :attr:`_execution_status`).

        Parameters
        ----------
        workflow : str
            The workflow ID to update.
        new_state : States
            The new :class:`~socm.utils.states.States` value to assign.
        """

        if workflow not in self._execution_status:
            self._logger.warning(
                "Has not enacted on workflow %s yet.",
                workflow,
                self._get_workflow_state(workflow),
            )
        else:
            self._execution_status[workflow]["state"] = new_state

    def _get_workflow_state(self, workflow):
        """
        Return the current state of a tracked workflow.

        Parameters
        ----------
        workflow : str
            The workflow ID to look up.

        Returns
        -------
        States
            The current :class:`~socm.utils.states.States` value for the workflow.
        """

        return self._execution_status[workflow]["state"]

    def terminate(self):
        """
        Terminate the enactor and clean up all managed resources.

        Must be overridden by concrete subclasses to cancel any in-flight
        pilot jobs or background threads.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("terminate is not implemented")

    def teardown(self):
        """
        Tear down the enactor's back-end, ensuring resources are released.

        Called between batches to cancel the current pilot before a new one
        is started. Must be overridden by concrete subclasses.

        Raises
        ------
        NotImplementedError
            Always raised by the base implementation.
        """
        raise NotImplementedError("teardown is not implemented")
