"""
Author: Ioannis Paraskevakos
License: MIT
Copyright: 2018-2019
"""

# Imports from general packages
import threading as mt
from copy import deepcopy
from datetime import datetime

import radical.pilot as rp

# Imports from dependent packages
import radical.utils as ru

from ..core import Resource
from ..utils import states as st
from .base import Enactor


class RPEnactor(Enactor):
    """
    The Emulated enactor is responsible to execute workflows on emulated
    resources. The Enactor takes as input a list of tuples <workflow,resource>
    and executes the workflows on their selected resources.
    """

    def __init__(self, sid):

        super(RPEnactor, self).__init__(sid=sid)

        # List with all the workflows that are executing and require to be
        # monitored. This list is atomic and requires a lock
        self._to_monitor = list()

        self._prof.prof("enactor_setup", uid=self._uid)
        # Lock to provide atomicity in the monitoring data structure
        self._monitoring_lock = ru.RLock("cm.monitor_lock")
        self._cb_lock = ru.RLock("enactor.cb_lock")
        self._callbacks = dict()

        # Creating a thread to execute the monitoring method.
        self._monitoring_thread = None  # Private attribute that will hold the thread
        self._terminate_monitor = mt.Event()  # Thread event to terminate.

        self._run = False
        self._prof.prof("enactor_started", uid=self._uid)
        self._rp_session = rp.Session(uid=sid)
        self._rp_pmgr = rp.PilotManager(session=self._rp_session)
        self._rp_tmgr = rp.TaskManager(session=self._rp_session)
        self._logger.info("Enactor is ready")

    def setup(self, resource: Resource, walltime: int, cores: int) -> None:
        """
        Sets up the enactor to execute workflows.
        """
        pd_init = {
            "resource": "princeton.tiger2",
            "runtime": walltime,  # pilot runtime (min)
            "exit_on_error": True,
            "queue": "tiger-test",
            "access_schema": "interactive",
            "cores": cores,
        }

        pdesc = rp.PilotDescription(pd_init)
        pilot = self._rp_pmgr.submit_pilots(pdesc)
        self._rp_tmgr.add_pilots(pilot)

        pilot.wait(state=rp.PMGR_ACTIVE)
        self._logger.info("Pilot is ready")

    def enact(self, workflows):
        """
        Method enact receives a set workflows and resources. It is responsible to
        start the execution of the workflow and set a endpoint to the WMF that
        executes the workflow

        *workflows:* A workflows that will execute on a resource
        *resources:* The resource that will be used.
        """

        self._prof.prof("enacting_start", uid=self._uid)
        exec_workflows = []
        for workflow in workflows:
            # If the enactor has already received a workflow issue a warning and
            # proceed.
            if workflow.id in self._execution_status:
                self._logger.info(
                    "Workflow %s is in state %s",
                    workflow,
                    st.state_dict[self._get_workflow_state(workflow.id)],
                )
                continue

            try:
                # Create a calculator task. This is equivalent because with
                # the emulated resources, a workflow is a number of operations
                # that need to be executed.

                exec_workflow = (
                    rp.TaskDescription()
                )  # Use workflow description and resources to create the TaskDescription
                exec_workflow.uid = f"workflow.{workflow.id}"
                exec_workflow.pre_exec = [
                    "module load openmpi/gcc/4.1.1/64" "module load anaconda3/2022.10",
                    "conda activate /scratch/gpfs/SIMONSOBS/env/20240517/soconda_3.10",
                ]
                exec_workflow.executable = "toast_env"
                exec_workflow.ranks = 1
                exec_workflow.cores_per_rank = 1

                self._logger.info("Enacting workflow %s", workflow.id)
                exec_workflows.append(exec_workflow)
                # Lock the monitoring list and update it, as well as update
                # the state of the workflow.
                with self._monitoring_lock:
                    self._to_monitor.append(workflow.id)
                    self._execution_status[workflow.id] = {
                        "state": st.EXECUTING,
                        "endpoint": exec_workflow,
                        "exec_thread": None,
                        "start_time": datetime.now(),
                        "end_time": None,
                    }
                for cb in self._callbacks:
                    self._callbacks[cb](
                        workflow_ids=[workflow.id], new_state=st.EXECUTING
                    )
                # Execute the task.
            except Exception as ex:
                self._logger.error(f"Workflow {workflow} could not be executed")
                self._logger.error(f"Exception raised {ex}")

        self._rp_tmgr.submit_tasks(exec_workflows)

        self._prof.prof("enacting_stop", uid=self._uid)
        # If there is no monitoring tasks, start one.
        if self._monitoring_thread is None:
            self._logger.info("Starting monitor thread")
            self._monitoring_thread = mt.Thread(
                target=self._monitor, name="monitor-thread"
            )
            self._monitoring_thread.start()

    def _monitor(self):
        """
        **Purpose**: Thread in the master process to monitor the campaign execution
                     data structure up to date.
        """

        while not self._terminate_monitor.is_set():
            if self._to_monitor:
                self._prof.prof("workflow_monitor_start", uid=self._uid)
                # with self._monitoring_lock:
                # It does not iterate correctly.
                monitoring_list = deepcopy(self._to_monitor)
                # self._logger.info("Monitoring workflows %s" % monitoring_list)
                to_remove = list()
                for workflow_id in monitoring_list:
                    rp_workflow = self._rp_tmgr.get_tasks(
                        uids=f"workflow.{workflow_id}"
                    )
                    if rp_workflow.state in rp.DONE:
                        with self._monitoring_lock:
                            self._logger.debug(f"workflow.{workflow_id} Done")
                            self._execution_status[workflow_id]["state"] = st.DONE
                            self._execution_status[workflow_id][
                                "end_time"
                            ] = datetime.now()
                            self._logger.debug(
                                "Workflow %s finished: %s",
                                workflow_id,
                                self._execution_status[workflow_id]["end_time"],
                            )
                            to_remove.append(workflow_id)
                        self._prof.prof("workflow_success", uid=self._uid)
                if to_remove:
                    for cb in self._callbacks:
                        self._callbacks[cb](workflow_ids=to_remove, new_state=st.DONE)
                    with self._monitoring_lock:
                        for wid in to_remove:
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
            status[workflow] = self._execution_status[workflow]["state"]

        return status

    def update_status(self, workflow, new_state):
        """
        Update the state of a workflow that is executing
        """

        if workflow not in self._execution_status:
            self._logger.warning(
                "Has not enacted on workflow %s yet.",
                workflow,
                self._get_workflow_state(workflow),
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
        # self._rp_tmgr.close()
        # self._rp_pmgr.close(terminate=True)
        self._rp_session.close(terminate=True)
        self._logger.debug("Simulation thread terminated")

    def register_state_cb(self, cb):
        """
        Registers a new state update callback function with the Enactor.
        """

        with self._cb_lock:
            cb_name = cb.__name__
            self._callbacks[cb_name] = cb
