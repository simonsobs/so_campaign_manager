import os
import threading as mt
from copy import deepcopy
from importlib.resources import files
from math import ceil, floor
from time import sleep
from typing import Dict

import numpy as np
import radical.utils as ru
from slurmise.api import Slurmise
from slurmise.job_data import JobData
from slurmise.slurm import parse_slurm_job_metadata

from ..core import Campaign, Resource
from ..enactor import RPEnactor
from ..planner import HeftPlanner
from ..utils import states as st


class Bookkeeper(object):
    """
    This is the Bookkeeping class. It gets the campaign and the resources, calls
    the planner and enacts to the plan.

    *Parameters:*

    *campaign:* The campaign that needs to be executed.
    *resources:* A set of resources.
    *objective:* The campaign's objective
    """

    def __init__(
        self,
        campaign: Campaign,
        resources: Dict[str, Resource],
        policy: str,
        target_resource: str,
    ):

        self._campaign = {"campaign": campaign, "state": st.NEW}
        self._session_id = ru.generate_id("socm.session", mode=ru.ID_PRIVATE)
        self._uid = ru.generate_id(
            "bookkeper.%(counter)04d", mode=ru.ID_CUSTOM, ns=self._session_id
        )

        self._resource = resources[target_resource]
        self._checkpoints = None
        self._plan = None
        self._plan_graph = None
        self._unavail_resources = []
        self._workflows_state = dict()
        self._workflows_execids = dict()
        self._objective = self._resource.maximum_walltime
        self._exec_state_lock = ru.RLock("workflows_state_lock")
        self._monitor_lock = ru.RLock("monitor_list_lock")
        self._slurmise = Slurmise(toml_path=files("socm.configs") / "slurmise.toml")
        # The time in the campaign's world. The first element is the actual time
        # of the campaign world. The second element is the
        # self._time = {"time": 0, "step": []}

        path = os.getcwd() + "/" + self._session_id

        self._logger = ru.Logger(name=self._uid, path=path, level="DEBUG")
        self._prof = ru.Profiler(name=self._uid, path=path)

        self._planner = HeftPlanner(
            sid=self._session_id,
            policy=policy,
            resources=self._resource,
        )
        # self._plan, self._plan_graph = self._planner.plan()
        # raise RuntimeError(
        #     "The Bookkeeper is not ready yet. Please use the new Bookkeeper class."
        # )
        self._workflows_to_monitor = list()
        self._est_end_times = dict()
        self._enactor = RPEnactor(sid=self._session_id)
        self._enactor.register_state_cb(self.state_update_cb)
        self._enactor.register_state_cb(self.workflowid_update_cb)

        # Creating a thread to execute the monitoring and work methods.
        # One flag for both threads may be enough  to monitor and check.
        self._terminate_event = mt.Event()  # Thread event to terminate.
        self._work_thread = None  # Private attribute that will hold the thread
        self._monitoring_thread = None  # Private attribute that will hold the thread

    def _get_campaign_requirements(self) -> Dict[str, Dict[str, float | int]]:

        workflow_requirements = dict()
        total_cores = self._resource.nodes * self._resource.cores_per_node
        total_memory = self._resource.nodes * self._resource.memory_per_node
        for workflow in self._campaign["campaign"].workflows:
            tmp_runtime = np.inf
            cores = 1
            while cores <= total_cores:
                slurm_job, _ = self._slurmise.predict(
                    cmd=workflow.get_command(), job_name=workflow.subcommand
                )
                self._logger.debug(
                    f"Slurm job prediction for {workflow.id}: {slurm_job}, "
                    f"runtime: {slurm_job.runtime}, memory: {slurm_job.memory}"
                )
                if (
                    tmp_runtime / slurm_job.runtime > 1.5
                    and slurm_job.memory < total_memory
                ):
                    tmp_runtime = slurm_job.runtime
                    cores *= 2
                else:
                    break
            if cores > total_cores:
                workflow_requirements[workflow.id] = {
                    "req_cpus": workflow.resources["ranks"],
                    "req_memory": workflow.resources["memory"],
                    "req_walltime": workflow.resources["runtime"]
                    * 1.1,  # Adding 10% to the runtime
                }
            else:
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
            if work[2] not in self._checkpoints:
                self._checkpoints.append(work[2])
            if work[3] not in self._checkpoints:
                self._checkpoints.append(work[3])

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

    def state_update_cb(self, workflow_ids, new_state, **kargs):
        """
        This is a state update callback. This callback is passed to the enactor.
        """
        self._logger.debug("Workflow %s to state %s", workflow_ids, new_state)
        with self._exec_state_lock:
            for workflow_id in workflow_ids:
                self._workflows_state[workflow_id] = new_state

    def workflowid_update_cb(self, workflow_ids, step_ids, **kargs):
        """
        This is a state update callback. This callback is passed to the enactor.
        """
        self._logger.debug("Workflow %s with slurmid %s", workflow_ids, step_ids)
        with self._exec_state_lock:
            for workflow_id, step_id in zip(workflow_ids, step_ids):
                self._workflows_execids[workflow_id] = step_id

    def work(self):
        """
        This method is responsible to execute the campaign.
        """

        # There is no need to check since I know there is no plan.
        self._logger.debug("Campaign state to PLANNING")
        self._prof.prof("planning_start", uid=self._uid)
        if self._plan is None:
            self._logger.debug("Calculating campaign plan")
            with self._exec_state_lock:
                self._campaign["state"] = st.PLANNING

            workflow_requirements = self._get_campaign_requirements()

            self._plan, self._plan_graph = self._planner.plan(
                campaign=self._campaign["campaign"].workflows,
                resource_requirements=workflow_requirements,
                start_time=0,
            )
            # self._plan = sorted(
            #     [place for place in self._plan], key=lambda place: place[-1]
            # )
            # self._logger.debug('Calculated plan: %s', self._plan)
        self._prof.prof("planning_ended", uid=self._uid)
        self._logger.debug("Calculated campaign plan")

        # Update checkpoints and objective.
        self._update_checkpoints()
        self._objective = int(
            ceil(min(self._checkpoints[-1] * 1.25, self._resource.maximum_walltime))
        )
        self._logger.debug(
            f"Campaign makespan {self._checkpoints[-1]}, and objective {self._objective}"
        )
        self._logger.debug(f"Resource max walltime {self._resource.maximum_walltime}")

        self._enactor.setup(
            resource=self._resource,
            walltime=self._objective,
            cores=self._resource.nodes * self._resource.cores_per_node,
        )

        with self._exec_state_lock:
            self._campaign["state"] = st.EXECUTING
        self._logger.debug("Campaign state to EXECUTING")

        self._prof.prof("work_start", uid=self._uid)
        while not self._terminate_event.is_set():
            if not self._verify_objective():
                self._logger.error("Objective cannot be satisfied. Ending execution")
                with self._exec_state_lock:
                    self._campaign["state"] = st.FAILED
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
                        or predecessors_states == set([st.DONE])
                    ) and self._workflows_state[wf_id] == st.NEW:
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
                    self._enactor.enact(
                        workflows=workflows,
                        core_requirements=cores,
                        memory_requirements=memory,
                    )
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
        This method monitors the state of the workflows. If the state is one of
        the final states, it removes the workflow from the monitoring list, and
        releases the resource. Otherwise if appends it to the end.
        """
        self._logger.info("Monitor thread started")
        while not self._terminate_event.is_set():
            while self._workflows_to_monitor:
                self._prof.prof("workflow_monitor", uid=self._uid)
                workflows = deepcopy(self._workflows_to_monitor)
                finished = list()
                # tmp_start_times = list()
                for i in range(len(workflows)):
                    if self._workflows_state[workflows[i].id] in st.CFINAL:
                        resource = self._unavail_resources[i]
                        finished.append((workflows[i], resource))
                        slurm_id, step_id = self._workflows_execids[
                            workflows[i].id
                        ].split(".")
                        workflow_metadata = parse_slurm_job_metadata(
                            slurm_id=slurm_id,
                            step_name=step_id,
                        )
                        workflow_jobdata = JobData(
                            job_name=workflows[i].name,
                            slurm_id=f"{slurm_id}.{slurm_id}",
                            categorical={},
                            numerical={},
                            memory=workflow_metadata["max_rss"],
                            runtime=workflow_metadata["elapsed_seconds"] / 60,
                            cmd=workflows[i].get_command(),
                        )
                        self._slurmise.raw_record(job_data=workflow_jobdata)
                        self._logger.info(
                            "Workflow %s finished",
                            workflows[i].id,
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
        Returns the makespan of the campaign based on the current state of
        execution
        """

        self._update_checkpoints()

        return self._checkpoints[-1]

    def terminate(self):

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
        This method starts two threads for executing the campaign. The first
        thread starts the work method. The second thread the monitoring thread.
        """
        try:
            # Populate the execution status dictionary with workflows
            with self._exec_state_lock:
                for workflow in self._campaign["campaign"].workflows:
                    self._workflows_state[workflow.id] = st.NEW
            self._prof.prof("bookkeper_start", uid=self._uid)
            self._logger.info("Starting work thread")
            self._work_thread = mt.Thread(target=self.work, name="work-thread")
            self._work_thread.start()
            self._logger.info("Starting monitor thread")
            self._monitoring_thread = mt.Thread(
                target=self.monitor, name="monitor-thread"
            )
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
            while self._campaign["state"] not in st.CFINAL:
                # Check if all workflows are in a final state.
                cont = False

                for workflow in self._campaign["campaign"].workflows:
                    if self._workflows_state[workflow.id] is st.FAILED:
                        self._campaign["state"] = st.FAILED
                        break
                    elif self._workflows_state[workflow.id] not in st.CFINAL:
                        cont = True

                if not cont:
                    self._campaign["state"] = st.DONE

            if self._campaign["state"] not in st.CFINAL:
                self._campaign["state"] = st.DONE
            self._prof.prof("bookkeper_stopping", uid=self._uid)
        except Exception as ex:
            self._logger.error(f"Exception occured: {ex}")
        finally:
            self.terminate()

    def get_campaign_state(self):

        return self._campaign["state"]

    def get_workflows_state(self):

        states = dict()
        for workflow in self._campaign["campaign"].workflows:
            states[workflow.id] = self._workflows_state[workflow.id]

        return states
