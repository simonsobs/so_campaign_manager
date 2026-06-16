# Imports from general packages
import os
import threading as mt
from copy import deepcopy
from datetime import datetime
from typing import Dict, List

# Imports from dependent packages
# import numpy as np  # noqa: F401
import radical.pilot as rp
import radical.utils as ru

from socm.core import Resource, Workflow
from socm.enactor.base import Enactor
from socm.utils.states import States


class RPEnactor(Enactor):
    """
    RADICAL-Pilot enactor for executing workflows on HPC resources via SLURM.

    Submits workflows to an HPC scheduler through RADICAL-Pilot (RP), monitors
    their progress via a background thread, and delivers state-change
    notifications to registered callbacks. Each workflow is translated into an
    ``rp.TaskDescription`` whose MPI rank and thread counts are derived from
    the workflow's :class:`~socm.core.models.ResourceSpec`.

    The RP session and pilot/task managers are created eagerly in
    ``__init__`` and remain active until :meth:`terminate` is called.  A
    single pilot per batch is submitted in :meth:`setup`; subsequent calls to
    :meth:`setup` (for successive batches) cancel the old pilot and create a
    new one.

    Parameters
    ----------
    sid : str
        Session ID used to construct namespaced log/profiler file paths and
        as the RADICAL-Pilot session UID.

    Attributes
    ----------
    _to_monitor : list of int
        Workflow IDs that have been submitted and are awaiting a final state.
    _monitoring_lock : radical.utils.RLock
        Lock protecting concurrent access to ``_to_monitor``.
    _cb_lock : radical.utils.RLock
        Lock protecting concurrent access to ``_callbacks``.
    _callbacks : dict of str to callable
        Registered state-change callbacks, keyed by callback function name.
    _monitoring_thread : threading.Thread or None
        Background thread running :meth:`_monitor`; started on first
        :meth:`enact` call.
    _terminate_monitor : threading.Event
        Set to signal the monitoring thread to stop.
    _pilot : radical.pilot.Pilot or None
        The currently active RP pilot. ``None`` before :meth:`setup` or after
        :meth:`teardown`.
    _rp_session : radical.pilot.Session
        The RADICAL-Pilot session.
    _rp_pmgr : radical.pilot.PilotManager
        The RADICAL-Pilot pilot manager.
    _rp_tmgr : radical.pilot.TaskManager
        The RADICAL-Pilot task manager.
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
        self._pilot = None
        self._rp_session = rp.Session(uid=sid)
        self._rp_pmgr = rp.PilotManager(session=self._rp_session)
        self._rp_tmgr = rp.TaskManager(session=self._rp_session)
        self._logger.info("Enactor is ready")

    def setup(self, resource: Resource, walltime: int, cores: int, execution_schema: str | None = None) -> None:
        """
        Submit a RADICAL-Pilot pilot job and wait for it to become active.

        Constructs a ``rp.PilotDescription`` from the resource name, walltime,
        and core count, submits it via the pilot manager, and blocks until the
        pilot reaches ``PMGR_ACTIVE`` state.

        Parameters
        ----------
        resource : Resource
            The HPC resource to execute workflows on. The resource ``name``
            is used to build the RP resource string ``"so.<name>"``.
        walltime : int
            Maximum walltime in minutes for the pilot job.
        cores : int
            Number of cores to request in the pilot.
        execution_schema : str or None, optional
            Access schema passed to RP. ``"batch"`` selects the SLURM batch
            schema; any other value (including ``None``) selects ``"local"``.
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
        self._pilot = self._rp_pmgr.submit_pilots(pdesc)
        self._rp_tmgr.add_pilots(self._pilot)

        self._pilot.wait(state=rp.PMGR_ACTIVE)
        self._logger.info("Pilot is ready")

    def enact(self, workflows: List[Workflow]) -> None:
        """
        Submit workflows for execution via RADICAL-Pilot.

        Translates each :class:`~socm.core.models.Workflow` into an
        ``rp.TaskDescription``, records the initial ``EXECUTING`` state,
        invokes registered callbacks, and submits all tasks to the RP task
        manager. Starts the monitoring background thread on the first call.

        Parameters
        ----------
        workflows : list of Workflow
            Workflows to submit. Already-submitted workflows (those present in
            :attr:`_execution_status`) are skipped with a warning.
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
                if hasattr(workflow, 'base_path'):
                    exec_workflow.sandbox = os.path.join(
                        workflow.base_path, f"{workflow.name}.{workflow.id}"
                    )
                exec_workflow.executable = workflow.executable
                exec_workflow.arguments = []
                if workflow.subcommand:
                    exec_workflow.arguments += [workflow.subcommand]
                exec_workflow.arguments += workflow.get_arguments()
                self._logger.debug(
                    "Workflow %s arguments: %s", workflow.id, exec_workflow.arguments
                )

                exec_workflow.ranks = workflow.resources.ranks
                exec_workflow.cores_per_rank = workflow.resources.threads
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

        Continuously polls RADICAL-Pilot task states for all workflow IDs in
        :attr:`_to_monitor`. When a task reaches a final RP state, the internal
        status is updated to ``DONE``, the SLURM job/step ID is extracted from
        the task's ``stdout``, and all registered callbacks are invoked with the
        completed workflow IDs and step IDs. Completed workflows are removed
        from :attr:`_to_monitor`.

        Runs until :attr:`_terminate_monitor` is set.
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
            A single workflow ID, a list of workflow IDs, or ``None`` to
            retrieve the state of every tracked workflow.

        Returns
        -------
        dict of str to States
            Mapping of workflow ID to its current
            :class:`~socm.utils.states.States` value.
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
        Update the execution state of a tracked workflow.

        Logs a warning if the workflow has not yet been submitted.

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

    def terminate(self):
        """
        Terminate the enactor, stopping the monitor thread and closing the RP session.

        Signals the monitoring thread to stop via :attr:`_terminate_monitor`,
        waits for it to join, then closes the pilot manager (which cancels the
        active pilot) and the RP session.
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
        self._rp_pmgr.close(terminate=True)
        self._rp_session.close(terminate=True)
        self._logger.debug("Enactor thread terminated")

    def register_state_cb(self, cb):
        """
        Register a callback function for workflow state updates.

        The callback will be invoked with keyword arguments
        ``workflow_ids``, ``new_state``, and ``step_ids`` whenever one or more
        workflows change state. Multiple callbacks can be registered; they are
        stored in :attr:`_callbacks` keyed by function name.

        Parameters
        ----------
        cb : callable
            The callback function to register.
        """

        with self._cb_lock:
            cb_name = cb.__name__
            self._callbacks[cb_name] = cb

    def teardown(self):
        """
        Cancel the active pilot and release its resources.

        Called between successive campaign batches so that a new pilot can be
        submitted for the next batch. If no pilot is active, logs a warning.
        """
        self._logger.info("Tearing down the Pilot")
        # No additional teardown needed for RADICAL-Pilot as terminate handles cleanup.
        if self._pilot:
            self._pilot.cancel()
            self._pilot.wait(state=rp.CANCELED)
            self._pilot = None
        else:
            self._logger.warning("No pilot to cancel during teardown.")
