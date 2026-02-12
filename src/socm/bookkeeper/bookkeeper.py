import os
import threading as mt
from importlib.resources import files
from math import ceil, floor
from pathlib import Path
from time import sleep
from typing import Dict

import radical.utils as ru
from slurmise.api import Slurmise
from slurmise.job_data import JobData
from slurmise.job_parse.file_parsers import FileMD5
from slurmise.slurm import parse_slurm_job_metadata

from ..core import Campaign, Workflow
from ..enactor import DryrunEnactor, RPEnactor
from ..planner import HeftPlanner
from ..resources import registered_resources
from ..utils.states import CFINAL, States


class Bookkeeper(object):
    """
    Main orchestrator for campaign execution on HPC systems.

    Coordinates the full lifecycle of a campaign: planning workflow
    schedules via the HEFT planner, submitting workflows to SLURM
    through an enactor (RADICAL-Pilot or dryrun), and monitoring
    their execution state. Uses Slurmise for job prediction and
    recording execution metadata.

    Parameters
    ----------
    campaign : Campaign
        The campaign containing workflows to execute.
    policy : str
        Scheduling policy passed to the HEFT planner.
    target_resource : str
        Name of the HPC resource (must be in ``registered_resources``).
    deadline : int
        Maximum walltime (in minutes) for the entire campaign.
    dryrun : bool, optional
        If True, use a dry-run enactor instead of RADICAL-Pilot.
        Defaults to False.
    """

    def __init__(
        self,
        campaign: Campaign,
        policy: str,
        target_resource: str,
        deadline: int,
        dryrun: bool = False,
    ):
        self._campaign = {"campaign": campaign, "state": States.NEW}
        self._session_id = ru.generate_id("socm.session", mode=ru.ID_PRIVATE)
        self._uid = ru.generate_id(
            "bookkeeper.%(counter)04d", mode=ru.ID_CUSTOM, ns=self._session_id
        )

        self._resource = registered_resources[target_resource]()
        self._checkpoints = None
        self._plan = None
        self._plan_graph = None
        self._unavail_resources = []
        self._workflows_state = dict()
        self._workflows_execids = dict()
        self._objective = deadline
        self._exec_state_lock = ru.RLock("workflows_state_lock")
        self._monitor_lock = ru.RLock("monitor_list_lock")
        self._slurmise = Slurmise(toml_path=files("socm.configs") / "slurmise.toml")
        # The time in the campaign's world. The first element is the actual time
        # of the campaign world. The second element is the
        # self._time = {"time": 0, "step": []}io

        path = os.getcwd() + "/" + self._session_id

        self._logger = ru.Logger(name=self._uid, path=path, level="DEBUG")
        self._prof = ru.Profiler(name=self._uid, path=path)
        self._logger.debug(f"Deadline {deadline}")
        self._planner = HeftPlanner(
            sid=self._session_id,
            policy=policy,
            resources=self._resource,
            objective=deadline
        )

        self._workflows_to_monitor = list()
        self._est_end_times = dict()
        self._enactor = RPEnactor(sid=self._session_id) if not dryrun else DryrunEnactor(sid=self._session_id)
        self._dryrun = dryrun
        self._enactor.register_state_cb(self.state_update_cb)
        self._enactor.register_state_cb(self.workflowid_update_cb)

        # Creating a thread to execute the monitoring and work methods.
        # One flag for both threads may be enough  to monitor and check.
        self._terminate_event = mt.Event()  # Thread event to terminate.
        self._work_thread = None  # Private attribute that will hold the thread
        self._monitoring_thread = None  # Private attribute that will hold the thread

    def _get_campaign_requirements(self) -> Dict[int, Dict[str, float]]:
        """
        Compute resource requirements for each workflow in the campaign.

        Attempts to predict resource needs via Slurmise. Falls back to
        user-specified workflow resources (with a 10% runtime buffer)
        when predictions are unavailable or produce warnings.

        Returns
        -------
        dict[int, dict[str, float]]
            Mapping of workflow ID to resource requirements containing
            ``req_cpus``, ``req_memory``, and ``req_walltime``.
        """
        workflow_requirements = dict()
        total_cores = 1 # self._resource.nodes * self._resource.cores_per_node
        # total_memory = self._resource.nodes * self._resource.memory_per_node
        for workflow in self._campaign["campaign"].workflows:
            # tmp_runtime = np.inf
            cores = 1
            while cores <= total_cores:
                self._logger.debug(
                    f"Workflow command: {workflow.get_command()} and subcommand: {workflow.subcommand}"
                )
                slurm_job, warns = (
                    None,
                    [1, 2],
                )
                # slurm_job, warns = self._slurmise.predict(cmd=workflow.get_command(), job_name=workflow.subcommand)
                # self._logger.debug(
                #     f"Slurm job prediction for {workflow.id}: {slurm_job}, "
                #     f"runtime: {slurm_job.runtime}, memory: {slurm_job.memory}"
                # )
                cores *= 2
                # if tmp_runtime / slurm_job.runtime > 1.5 and slurm_job.memory < total_memory:
                #     tmp_runtime = slurm_job.runtime
                #     cores *= 2
                # else:
                #     break

            if cores > total_cores or len(warns) > 0:
                workflow_requirements[workflow.id] = {
                    "req_cpus": workflow.resources["ranks"]
                    * workflow.resources["threads"],
                    "req_memory": workflow.resources["memory"],
                    "req_walltime": workflow.resources["runtime"]
                    * 1.1,  # Adding 10% to the runtime
                }
            else:
                workflow.resources["ranks"] = cores // 2
                workflow.resources["threads"] = 1
                workflow.resources["memory"] = slurm_job.memory
                workflow_requirements[workflow.id] = {
                    "req_cpus": cores // 2,
                    "req_memory": slurm_job.memory,
                    "req_walltime": slurm_job.runtime
                    * 1.1,  # Adding 10% to the runtime
                }
        return workflow_requirements

    def _update_checkpoints(self):
        """
        Create a list of timestamps when workflows may start executing or end.
        """

        self._checkpoints = [0]

        for work in self._plan:
            if work[-2] not in self._checkpoints:
                self._checkpoints.append(work[-2])
            if work[-1] not in self._checkpoints:
                self._checkpoints.append(work[-1])

        self._checkpoints.sort()

    def _verify_objective(self):
        """
        This private method verifies that the plan has not deviated from the
        maximum walltime. It checks the estimated makespan of the campaign and
        compares it with the maximum walltime.
        """

        self._update_checkpoints()

        if self._checkpoints[-1] > self._objective:
            return False
        else:
            return True

    def _record(self, workflow: Workflow) -> None:
        """
        Record workflow execution data to Slurmise for future predictions.

        Parses SLURM job metadata (runtime, memory) and combines it with
        workflow-specific numerical and categorical fields to build a
        ``JobData`` record. Skipped during dry-run mode.

        Parameters
        ----------
        workflow : Workflow
            The completed workflow whose execution data should be recorded.
        """
        if self._dryrun:
            return

        self._logger.debug(
            f"Recording workflow {workflow.id} with execid {self._workflows_execids[workflow.id]}"
        )
        slurm_id, step_id = self._workflows_execids[workflow.id].split(".")
        workflow_metadata = parse_slurm_job_metadata(
            slurm_id=slurm_id,
            step_name=step_id,
        )

        numerical_fields = {
            "ranks": workflow.resources["ranks"],
            "threads": workflow.resources["threads"],
        }
        for field in workflow.get_numeric_fields(avoid_attributes=["id"]):
            numerical_fields[field] = getattr(workflow, field)

        categorical_fields = {}
        for field in workflow.get_categorical_fields(
            avoid_attributes=["executable", "name", "context", "output_dir", "query"]
        ):
            val = getattr(workflow, field)
            field_val = (
                FileMD5().parse_file(Path(val.split("file://")[-1]).absolute())
                if val.startswith("file://")
                else val
            )
            categorical_fields[field] = field_val

        workflow_jobdata = JobData(
            job_name=workflow.name,
            slurm_id=f"{slurm_id}.{step_id}",
            categorical=categorical_fields,
            numerical=numerical_fields,
            memory=workflow_metadata["max_rss"],
            runtime=workflow_metadata["elapsed_seconds"] / 60,
            cmd=workflow.get_command(),
        )
        self._logger.debug(
            "Workflow %s finished with metadata: %s and jobdata: %s",
            workflow.id,
            workflow_metadata,
            workflow_jobdata,
        )
        self._slurmise.raw_record(job_data=workflow_jobdata)

    def state_update_cb(self, workflow_ids, new_state, **kargs):
        """
        Callback invoked by the enactor when workflow states change.

        Parameters
        ----------
        workflow_ids : list[str]
            IDs of the workflows whose state changed.
        new_state : States
            The new execution state for the workflows.
        """
        self._logger.debug("Workflow %s to state %s", workflow_ids, new_state.name)
        with self._exec_state_lock:
            for workflow_id in workflow_ids:
                self._workflows_state[workflow_id] = new_state

    def workflowid_update_cb(self, workflow_ids, step_ids, **kargs):
        """
        Callback invoked by the enactor to map workflow IDs to SLURM step IDs.

        Parameters
        ----------
        workflow_ids : list[str]
            IDs of the workflows.
        step_ids : list[str]
            Corresponding SLURM job/step IDs (format: ``slurm_id.step_id``).
        """
        self._logger.debug("Workflow %s with slurmid %s", workflow_ids, step_ids)
        with self._exec_state_lock:
            for workflow_id, step_id in zip(workflow_ids, step_ids):
                self._workflows_execids[workflow_id] = step_id

    def work(self):
        """
        Execute the campaign by planning and submitting workflows.

        Runs in a dedicated thread. Computes the execution plan via the
        HEFT planner, verifies the campaign can meet its deadline, sets up
        the enactor with the required resources, and continuously submits
        workflows whose dependencies have been satisfied. Respects the
        DAG dependency order from the plan graph.
        """

        # There is no need to check since I know there is no plan.
        self._logger.debug("Campaign state to PLANNING")
        self._prof.prof("planning_start", uid=self._uid)
        if self._plan is None:
            self._logger.debug("Calculating campaign plan")
            with self._exec_state_lock:
                self._campaign["state"] = States.PLANNING

            workflow_requirements = self._get_campaign_requirements()

            self._plan, self._plan_graph, selected_qos, cores_request = self._planner.plan(
                campaign=self._campaign["campaign"].workflows,
                execution_schema=self._campaign["campaign"].execution_schema,
                resource_requirements=workflow_requirements,
                requested_resources=self._campaign["campaign"].requested_resources
            )

        self._prof.prof("planning_ended", uid=self._uid)
        self._logger.debug(f"Calculated campaign plan with {selected_qos} QOS and requesting {cores_request} cores")

        # Update checkpoints and objective.
        self._update_checkpoints()
        if not self._verify_objective():
            self._logger.error("Objective cannot be satisfied. Ending execution")
            with self._exec_state_lock:
                self._campaign["state"] = States.FAILED
            sleep(1)
            return

        self._objective = int(
            ceil(min(self._checkpoints[-1] * 1.25, self._objective))
        )
        self._logger.debug(
            f"Campaign makespan {self._checkpoints[-1]}, and objective {self._objective}"
        )
        self._logger.debug(f"Resource max walltime {self._objective}")

        self._enactor.setup(
            resource=self._resource,
            walltime=self._objective,
            cores=cores_request,
            execution_schema=self._campaign["campaign"].execution_schema,
        )

        with self._exec_state_lock:
            self._campaign["state"] = States.EXECUTING
        self._logger.debug("Campaign state to EXECUTING")

        self._prof.prof("work_start", uid=self._uid)
        while not self._terminate_event.is_set():
            if not self._verify_objective():
                self._logger.error("Objective cannot be satisfied. Ending execution")
                with self._exec_state_lock:
                    self._campaign["state"] = States.FAILED
                    # self.terminate()
            else:
                self._prof.prof("work_submit", uid=self._uid)
                workflows = list()  # Workflows to enact
                cores = list()  # The selected cores
                memory = list()  # The memory per workflow

                for wf_id in self._plan_graph.nodes():

                    predecessors_states = set()
                    for predecessor in self._plan_graph.predecessors(wf_id):
                        predecessors_states.add(self._workflows_state[predecessor])
                    # Do not enact to workflows that sould have been executed
                    # already.
                    if (
                        predecessors_states == set()
                        or predecessors_states == set([States.DONE])
                    ) and self._workflows_state[wf_id] == States.NEW:
                        node_slice = (
                            self._plan[wf_id - 1][2] / self._resource.memory_per_node
                        )
                        threads_per_core = floor(
                            self._resource.cores_per_node
                            * node_slice
                            / len(self._plan[wf_id - 1][1])
                        )
                        # print(node_slice, threads_per_core, self._plan[wf_id - 1])
                        workflows.append(self._plan[wf_id - 1][0])
                        cores.append((self._plan[wf_id - 1][1], threads_per_core))
                        memory.append(self._plan[wf_id - 1][2])

                        self._logger.debug(
                            f"To submit workflows {[x for x in workflows]}"
                            + f" to resources {cores}"
                        )

                        for rc_id in self._plan[wf_id - 1][1]:
                            self._est_end_times[rc_id] = self._plan[wf_id - 1][3]
                if workflows:
                    self._logger.debug(
                        f"Submitting workflows {[x.id for x in workflows]}"
                        + f" to resources {cores}"
                    )

                # There is no need to call the enactor when no new things
                # should happen.
                # self._logger.debug('Adding items: %s, %s', workflows, resources)
                if workflows and cores and memory:
                    self._prof.prof("enactor_submit", uid=self._uid)
                    self._enactor.enact(workflows=workflows)
                    self._prof.prof("enactor_submitted", uid=self._uid)

                    with self._monitor_lock:
                        self._workflows_to_monitor += workflows
                        self._unavail_resources += cores
                        self._logger.info(
                            f"Total number of workflows to monitor {len(workflows)}"
                        )
                    self._logger.debug(
                        "Things monitored: %s, %s, %s",
                        self._workflows_to_monitor,
                        self._unavail_resources,
                        self._est_end_times,
                    )

                self._prof.prof("work_submitted", uid=self._uid)
            sleep(1)

    def monitor(self):
        """
        Monitor running workflows and release resources upon completion.

        Runs in a dedicated thread. Continuously checks workflow states
        and, for any that have reached a final state, records their
        execution data via Slurmise and removes them from the active
        monitoring list along with their allocated resources.
        """
        self._logger.info("Monitor thread started")
        while not self._terminate_event.is_set():
            while self._workflows_to_monitor:
                self._prof.prof("workflow_monitor", uid=self._uid)
                with self._monitor_lock:
                    workflows_snapshot = list(self._workflows_to_monitor)
                finished = list()
                for i in range(len(workflows_snapshot)):
                    if self._workflows_state[workflows_snapshot[i].id] in CFINAL:
                        resource = self._unavail_resources[i]
                        finished.append((workflows_snapshot[i], resource))

                        self._record(workflows_snapshot[i])
                        self._logger.info(
                            "Workflow %s finished",
                            workflows_snapshot[i].id,
                        )

                if finished:
                    with self._monitor_lock:
                        for workflow, resource in finished:
                            self._workflows_to_monitor.remove(workflow)
                            self._unavail_resources.remove(resource)
                    self._prof.prof("workflow_finished", uid=self._uid)
                else:
                    sleep(1)  # Sleep for a while if nothing happened.

        self._logger.debug("Monitor thread Stoped")

    def get_makespan(self):
        """
        Return the estimated makespan of the campaign.

        Returns
        -------
        float
            The latest checkpoint time, representing the expected
            completion time of the entire campaign (in minutes).
        """

        self._update_checkpoints()

        return self._checkpoints[-1]

    def terminate(self):
        """
        Gracefully shut down the bookkeeper and all managed threads.

        Terminates the enactor, signals the work and monitor threads
        to stop, and waits for them to join.
        """
        self._logger.info("Start terminating procedure")
        self._prof.prof("str_bookkeper_terminating", uid=self._uid)

        # Terminate enactor as well.
        self._enactor.terminate()

        # Terminate your threads.
        self._logger.debug("Enactor terminated, terminating threads")

        self._terminate_event.set()  # Thread event to terminate.

        self._prof.prof("monitor_bookkeper_terminate", uid=self._uid)
        if self._monitoring_thread:
            self._monitoring_thread.join()
        self._prof.prof("monitor_bookkeper_terminated", uid=self._uid)
        self._logger.debug("Monitor thread terminated")

        self._prof.prof("work_bookkeper_terminate", uid=self._uid)
        if self._work_thread:
            self._work_thread.join()  # Private attribute that will hold the thread
        self._prof.prof("work_bookkeper_terminated", uid=self._uid)
        self._logger.debug("Working thread terminated")

    def run(self):
        """
        Run the campaign to completion.

        Initializes workflow states, spawns the work and monitor threads,
        then blocks until all workflows reach a final state (DONE or
        FAILED). Calls ``terminate()`` on exit regardless of outcome.
        """
        try:
            # Populate the execution status dictionary with workflows
            with self._exec_state_lock:
                for workflow in self._campaign["campaign"].workflows:
                    self._workflows_state[workflow.id] = States.NEW
            self._prof.prof("bookkeper_start", uid=self._uid)
            self._logger.info("Starting work thread")
            self._work_thread = mt.Thread(target=self.work, name=f"bookkeeper-{self._uid}-work")
            self._work_thread.start()
            self._logger.info("Starting monitor thread")
            self._monitoring_thread = mt.Thread(target=self.monitor, name=f"bookkeeper-{self._uid}-monitor")
            self._monitoring_thread.start()
            self._prof.prof("bookkeper_started", uid=self._uid)

            # This waits regardless if workflows are failing or not. This loop can
            # do meaningful work such as checking the state of the campaign. It can
            # be a while true, until something happens.
            # self._logger.debug(
            #     "Time now: %s, checkpoints: %s", self._time, self._checkpoints
            # )
            while self._checkpoints is None:
                continue

            self._prof.prof("bookkeper_wait", uid=self._uid)
            while self._campaign["state"] not in CFINAL:
                # Check if all workflows are in a final state.
                cont = False

                for workflow in self._campaign["campaign"].workflows:
                    if self._workflows_state[workflow.id] is States.FAILED:
                        self._campaign["state"] = States.FAILED
                        break
                    elif self._workflows_state[workflow.id] not in CFINAL:
                        cont = True

                if not cont and not self._workflows_to_monitor:
                    self._campaign["state"] = States.DONE

            if self._campaign["state"] not in CFINAL:
                self._campaign["state"] = States.DONE
            self._prof.prof("bookkeper_stopping", uid=self._uid)
        except Exception as ex:
            self._logger.error(f"Exception occured: {ex}")
        finally:
            self.terminate()

    def get_campaign_state(self):
        """Return the current state of the campaign."""
        return self._campaign["state"]

    def get_workflows_state(self):
        """
        Return the current state of every workflow in the campaign.

        Returns
        -------
        dict[str, States]
            Mapping of workflow ID to its current execution state.
        """
        states = dict()
        for workflow in self._campaign["campaign"].workflows:
            states[workflow.id] = self._workflows_state[workflow.id]

        return states
