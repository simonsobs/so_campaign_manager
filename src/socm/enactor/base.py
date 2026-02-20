import os
from typing import Dict, List

import radical.utils as ru

from socm.core import Resource
from socm.utils.states import States


class Enactor(object):
    """
    The Enactor is responsible for executing workflows on resources.

    The Enactor takes as input a list of workflows and executes them on
    their selected resources. It offers methods to execute and monitor
    workflow execution.

    Attributes
    ----------
    _worflows : list
        A list with the workflow IDs that are executing.
    _execution_status : dict
        A hash table that holds the state and execution status of each
        workflow.
    _logger : ru.Logger
        A logging object.
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

        Parameters
        ----------
        resource : Resource
            The HPC resource to execute workflows on.
        walltime : int
            Maximum walltime in minutes for the pilot job.
        cores : int
            Number of cores to request.
        execution_schema : str or None, optional
            The access schema (e.g., 'batch' or 'local').
        """
        raise NotImplementedError("setup is not implemented")

    def enact(self, workflows, resources):
        """
        Submit workflows for execution.

        Parameters
        ----------
        workflows : list
            A list of workflows to execute.
        resources : Resource
            The resource to execute the workflows on.
        """
        raise NotImplementedError("enact is not implemented")

    def _monitor(self):
        """Monitor the execution status of submitted workflows."""

        raise NotImplementedError("_monitor is not implemented")

    def get_status(self, workflows: str | List[str] | None = None) -> Dict[str, States]:
        """
        Get the execution state of one or more workflows.

        Parameters
        ----------
        workflows : str, list of str, or None, optional
            A workflow ID, a list of workflow IDs, or None to get all.

        Returns
        -------
        dict
            A dictionary mapping workflow IDs to their current state.
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
        Update the execution state of a workflow via callback.

        Parameters
        ----------
        workflow : str
            The workflow ID to update.
        new_state : States
            The new state to set for the workflow.
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
        Get the current state of a workflow.

        Parameters
        ----------
        workflow : str
            The workflow ID.

        Returns
        -------
        States
            The current state of the workflow.
        """

        return self._execution_status[workflow]["state"]

    def terminate(self):
        """Terminate the Enactor and clean up resources."""
        raise NotImplementedError("terminate is not implemented")
