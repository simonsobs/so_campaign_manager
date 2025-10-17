# Imports from general packages
import os
import threading as mt
from copy import deepcopy
from datetime import datetime
from time import sleep
from typing import List

# Imports from dependent packages
import radical.utils as ru

from socm.core import Resource, Workflow
from socm.enactor.base import Enactor
from socm.utils.states import States


class DryrunEnactor(Enactor):
    """
    The DryrunEnactor is responsible for simulating the execution of workflows
    on resources without actually running them. It takes as input a list of
    tuples <workflow, resource> and emulates the execution of workflows on their
    selected resources for testing and validation purposes.
    """

    def __init__(self, sid: str):
        super(DryrunEnactor, self).__init__(sid=sid)
        # List with all the workflows that are executing and require to be
        # monitored. This list is atomic and requires a lock
        self._to_monitor = list()

        os.environ["RADICAL_CONFIG_USER_DIR"] = os.path.join(
            os.path.dirname(__file__) + "/../configs/"
        )
        self._prof.prof("enactor_setup", uid=self._uid)
        # Lock to provide atomicity in the monitoring data structure
        self._monitoring_lock = ru.RLock("cm.monitor_lock")
        self._cb_lock = ru.RLock("enactor.cb_lock")
        self._callbacks = dict()

        # Creating a thread to execute the monitoring method.
        self._monitoring_thread = None  # Private attribute that will hold the thread
        self._terminate_monitor = mt.Event()  # Thread event to terminate.

        self._run = False
        self._resource = None
        self._prof.prof("enactor_started", uid=self._uid)
        self._logger.info("Enactor is ready")

    def setup(self, resource: Resource, walltime: int, cores: int) -> None:
        """
        Sets up the enactor to execute workflows.
        """
        self._resource = resource


    def enact(self, workflows: List[Workflow]) -> None:
        """
        Method enact receives a set workflows and resources. It is responsible to
        start the execution of the workflow and set a endpoint to the WMF that
        executes the workflow

        *workflows:* A workflows that will execute on a resource
        *resources:* The resource that will be used.
        """

        self._prof.prof("enacting_start", uid=self._uid)
        for workflow in workflows:
            # If the enactor has already received a workflow issue a warning and
            # proceed.
            if workflow.id in self._execution_status:
                self._logger.info(
                    "Workflow %s is in state %s",
                    workflow,
                    self._get_workflow_state(workflow.id).name,
                )
                continue

            try:
                # Create a calculator task. This is equivalent because with
                # the emulated resources, a workflow is a number of operations
                # that need to be executed.

                with self._monitoring_lock:
                    self._to_monitor.append(workflow.id)
                    self._execution_status[workflow.id] = {
                        "state": States.EXECUTING,
                        "exec_thread": None,
                        "start_time": datetime.now(),
                        "end_time": None,
                    }

                for cb in self._callbacks:
                    self._callbacks[cb](
                        workflow_ids=[workflow.id],
                        new_state=States.EXECUTING,
                        step_ids=[None],
                    )
                # Execute the task.
            except Exception as ex:
                self._logger.error(f"Workflow {workflow} could not be executed")
                self._logger.error(f"Exception raised {ex}", exc_info=True)

        self._prof.prof("enacting_stop", uid=self._uid)
        # If there is no monitoring tasks, start one.
        if self._monitoring_thread is None and self._to_monitor:
            self._logger.info("Starting monitor thread")
            self._monitoring_thread = mt.Thread(
                target=self._monitor, name="monitor-thread"
            )
            self._monitoring_thread.start()
        sleep(1)

    def _monitor(self):
        """
        **Purpose**: Thread in the master process to monitor the campaign execution
                     data structure up to date.
        """

        while not self._terminate_monitor.is_set():
            if self._to_monitor:
                workflows_executing = [f"workflow.{workflow_id}" for workflow_id in self._to_monitor]
                self._prof.prof("workflow_monitor_start", uid=self._uid)
                # with self._monitoring_lock:
                # It does not iterate correctly.
                monitoring_list = deepcopy(self._to_monitor)
                # self._logger.info("Monitoring workflows %s" % monitoring_list)
                to_remove_wfs = list()
                to_remove_sids = list()
                self._logger.debug(f"Executing workflows: {workflows_executing}, monitoring list: {monitoring_list}")
                for workflow_id in monitoring_list:
                    if f"workflow.{workflow_id}" in workflows_executing:
                        with self._monitoring_lock:
                            self._logger.debug(f"workflow.{workflow_id} Done")
                            self._execution_status[workflow_id]["state"] = States.DONE
                            self._execution_status[workflow_id][
                                "end_time"
                            ] = datetime.now()
                            self._logger.debug(
                                "Workflow %s finished: %s, step_id: %s",
                                workflow_id,
                                self._execution_status[workflow_id]["end_time"],
                                0,
                            )
                            to_remove_wfs.append(workflow_id)
                            to_remove_sids.append(0)
                        self._prof.prof("workflow_success", uid=self._uid)
                if to_remove_wfs:
                    for cb in self._callbacks:
                        self._callbacks[cb](
                            workflow_ids=to_remove_wfs,
                            new_state=States.DONE,
                            step_ids=to_remove_sids,
                        )
                    with self._monitoring_lock:
                        for wid in to_remove_wfs:
                            self._to_monitor.remove(wid)
                self._prof.prof("workflow_monitor_end", uid=self._uid)

    def get_status(self, workflows=None):
        """
        Get the state of a workflow or workflows.

        *Parameter*
        *workflows:* A workflow ID or a list of workflow IDs

        *Returns*
        *status*: A dictionary with the state of each workflow.
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

    def update_status(self, workflow, new_state):
        """
        Update the state of a workflow that is executing
        """

        if workflow not in self._execution_status:
            self._logger.warning(
                "Has not enacted on workflow %s yet.",
                workflow,
            )
        else:
            self._execution_status[workflow]["state"] = new_state

    def terminate(self):
        """
        Public method to terminate the Enactor
        """
        self._logger.info("Start terminating procedure")
        self._prof.prof("str_terminating", uid=self._uid)
        if self._monitoring_thread:
            self._prof.prof("monitor_terminate", uid=self._uid)
            self._terminate_monitor.set()
            self._monitoring_thread.join()
            self._prof.prof("monitor_terminated", uid=self._uid)
        self._logger.debug("Monitor thread terminated")
        self._logger.debug("Enactor thread terminated")

    def register_state_cb(self, cb):
        """
        Registers a new state update callback function with the Enactor.
        """

        with self._cb_lock:
            cb_name = cb.__name__
            self._callbacks[cb_name] = cb
