# Imports from general packages
import os
import threading as mt
from copy import deepcopy
from datetime import datetime
from typing import Dict, List

# Imports from dependent packages
import numpy as np  # noqa: F401
import radical.pilot as rp
import radical.utils as ru

from socm.core import Resource, Workflow
from socm.enactor.base import Enactor
from socm.utils.states import States


class RPEnactor(Enactor):
    """
    RADICAL-Pilot enactor for executing workflows on HPC resources.

    The RPEnactor submits workflows to SLURM via RADICAL-Pilot and monitors
    their execution. It takes a list of workflows, creates RP TaskDescriptions,
    and submits them through a pilot job.
    """

    def __init__(self, sid: str):
        super(RPEnactor, self).__init__(sid=sid)
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
        self._rp_session = rp.Session(uid=sid)
        self._rp_pmgr = rp.PilotManager(session=self._rp_session)
        self._rp_tmgr = rp.TaskManager(session=self._rp_session)
        self._logger.info("Enactor is ready")

    def setup(self, resource: Resource, walltime: int, cores: int, execution_schema: str | None = None) -> None:
        """
        Set up the RADICAL-Pilot session and submit a pilot job.

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
        self._resource = resource

        pd_init = {
            "resource": f"so.{resource.name}",
            "runtime": walltime,  # pilot runtime (min)
            "exit_on_error": True,
            "access_schema": "batch" if execution_schema == "batch" else "local",
            "cores": cores,
            "project": "simonsobs",
        }

        pdesc = rp.PilotDescription(pd_init)
        self._logger.debug(f"Asking for {pdesc} pilot")
        pilot = self._rp_pmgr.submit_pilots(pdesc)
        self._rp_tmgr.add_pilots(pilot)

        pilot.wait(state=rp.PMGR_ACTIVE)
        self._logger.info("Pilot is ready")

    def enact(self, workflows: List[Workflow]) -> None:
        """
        Submit workflows for execution via RADICAL-Pilot.

        Parameters
        ----------
        workflows : list of Workflow
            The workflows to submit for execution.
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
                    self._get_workflow_state(workflow.id).name,
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

                exec_workflow.executable = workflow.executable
                exec_workflow.arguments = []
                if workflow.subcommand:
                    exec_workflow.arguments += [workflow.subcommand]
                exec_workflow.arguments += workflow.get_arguments()
                self._logger.debug(
                    "Workflow %s arguments: %s", workflow.id, exec_workflow.arguments
                )

                exec_workflow.ranks = workflow.resources["ranks"]
                exec_workflow.cores_per_rank = workflow.resources["threads"]
                exec_workflow.threading_type = rp.OpenMP
                # exec_workflow.mem_per_rank = np.ceil(
                #     workflow.resources["memory"] / workflow.resources["ranks"]
                # )  # this translates to memory per rank
                exec_workflow.post_exec = "echo ${SLURM_JOB_ID}.${SLURM_STEP_ID}"
                if workflow.environment:
                    exec_workflow.environment = workflow.environment
                self._logger.info("Enacting workflow %s", workflow.id)
                exec_workflows.append(exec_workflow)
                # Lock the monitoring list and update it, as well as update
                # the state of the workflow.
                with self._monitoring_lock:
                    self._to_monitor.append(workflow.id)
                    self._execution_status[workflow.id] = {
                        "state": States.EXECUTING,
                        "endpoint": exec_workflow,
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
        Monitor submitted workflows in a background thread.

        Polls RADICAL-Pilot task states and updates the internal execution
        status. Invokes registered callbacks when workflows complete.
        """

        self._prof.prof("workflow_monitor_start", uid=self._uid)
        while not self._terminate_monitor.is_set():
            if self._to_monitor:
                workflows_executing = self._rp_tmgr.list_tasks()
                # with self._monitoring_lock:
                # It does not iterate correctly.
                monitoring_list = deepcopy(self._to_monitor)
                # self._logger.info("Monitoring workflows %s" % monitoring_list)
                to_remove_wfs = list()
                to_remove_sids = list()

                for workflow_id in monitoring_list:
                    if f"workflow.{workflow_id}" in workflows_executing:
                        rp_workflow = self._rp_tmgr.get_tasks(
                            uids=f"workflow.{workflow_id}"
                        )
                        if rp_workflow.state in rp.FINAL:
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
                                    rp_workflow.stdout.split()[-1],
                                )
                                to_remove_wfs.append(workflow_id)
                                to_remove_sids.append(rp_workflow.stdout.split()[-1])
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

    def update_status(self, workflow, new_state):
        """
        Update the execution state of a workflow.

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

    def terminate(self):
        """Terminate the Enactor, monitor thread, and RADICAL-Pilot session."""
        self._logger.info("Start terminating procedure")
        self._prof.prof("str_terminating", uid=self._uid)
        if self._monitoring_thread:
            self._prof.prof("monitor_terminate", uid=self._uid)
            self._terminate_monitor.set()
            self._monitoring_thread.join()
            self._prof.prof("monitor_terminated", uid=self._uid)
        self._logger.debug("Monitor thread terminated")
        # self._rp_tmgr.close()
        self._rp_pmgr.close(terminate=True)
        self._rp_session.close(terminate=True)
        self._logger.debug("Enactor thread terminated")

    def register_state_cb(self, cb):
        """
        Register a callback function for workflow state updates.

        Parameters
        ----------
        cb : callable
            A callback function invoked when workflow states change.
        """

        with self._cb_lock:
            cb_name = cb.__name__
            self._callbacks[cb_name] = cb
