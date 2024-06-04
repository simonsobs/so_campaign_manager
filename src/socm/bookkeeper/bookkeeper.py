import os
import threading as mt
from copy import deepcopy
from time import sleep
from typing import Dict
from datetime import datetime

import radical.utils as ru

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
        self._objective = self._resource.maximum_walltime
        self._exec_state_lock = ru.RLock("workflows_state_lock")
        self._monitor_lock = ru.RLock("monitor_list_lock")
        # The time in the campaign's world. The first element is the actual time
        # of the campaign world. The second element is the
        self._time = {"time": 0, "step": []}

        self._workflows_to_monitor = list()
        self._est_end_times = dict()
        self._enactor = RPEnactor(sid=self._session_id)
        self._enactor.register_state_cb(self.state_update_cb)

        # Creating a thread to execute the monitoring and work methods.
        # One flag for both threads may be enough  to monitor and check.
        self._terminate_event = mt.Event()  # Thread event to terminate.
        self._work_thread = None  # Private attribute that will hold the thread
        self._monitoring_thread = None  # Private attribute that will hold the thread
        self._cont = False
        self._hold = False

        path = os.getcwd() + "/" + self._session_id

        self._logger = ru.Logger(name=self._uid, path=path, level="DEBUG")
        self._prof = ru.Profiler(name=self._uid, path=path)

        workflow_requirements = {}
        for workflow in self._campaign["campaign"].workflows:
            req_cpus, req_memory = workflow.get_num_cores_memory(self._resource)
            req_walltime = workflow.get_expected_execution_time(self._resource)
            workflow_requirements[workflow.id] = {
                "req_cpus": req_cpus,
                "req_memory": req_memory,
                "req_walltime": req_walltime,
            }

        self._planner = HeftPlanner(
            campaign=self._campaign["campaign"].workflows,
            resources=self._resource,
            resource_requirements=workflow_requirements,
            sid=self._session_id,
            policy=policy,
        )

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

    def state_update_cb(self, workflow_ids, new_state):
        """
        This is a state update callback. This callback is passed to the enactor.
        """
        self._logger.debug("Workflow %s to state %s", workflow_ids, new_state)
        with self._exec_state_lock:
            for workflow_id in workflow_ids:
                self._workflows_state[workflow_id] = new_state
        # if new_state is st.DONE:
        #    self._hold = True

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
            self._plan, self._plan_graph = self._planner.plan()
            self._plan = sorted(
                [place for place in self._plan], key=lambda place: place[-1]
            )
            # self._logger.debug('Calculated plan: %s', self._plan)
        self._prof.prof("planning_ended", uid=self._uid)
        self._logger.debug("Calculated campaign plan")

        # Update checkpoints and objective.
        self._update_checkpoints()
        self._objective = min(
            self._checkpoints[-1] * 1.25, self._resource.maximum_walltime
        )
        self._logger.debug(
            f"Campaign makespan {self._checkpoints[-1]}, and objective {self._objective}"
        )
        self._logger.debug(f"Resource max walltime {self._resource.maximum_walltime}")

        self._enactor.setup(resource="tiger", walltime=30, cores=40)

        with self._exec_state_lock:
            self._campaign["state"] = st.EXECUTING
        self._logger.debug("Campaign state to EXECUTING")

        self._prof.prof("work_start", uid=self._uid)
        while not self._terminate_event.is_set():
            if not self._verify_objective():
                self._logger.error("Objective cannot be satisfied. Ending execution")
                with self._exec_state_lock:
                    self._campaign["state"] = st.FAILED
                    self._terminate()
            else:

                self._prof.prof("work_submit", uid=self._uid)
                workflows = list()  # Workflows to enact
                resources = list()  # The selected resources
                self._logger.debug(f"Checking workflows {self._hold}, {self._cont}")
                while (not self._cont) or self._hold:
                    continue
                # self._logger.debug(f"Plan {self._plan}")
                for wf, rc, start_time, est_end_time in self._plan:
                    self._logger.debug(
                        f"{wf}, {rc}, {start_time}, {self._time['time']}, {est_end_time}"
                    )
                    # Do not enact to workflows that sould have been executed
                    # already.
                    if (
                        start_time == self._time["time"]
                        and est_end_time > self._time["time"]
                        and rc not in self._unavail_resources
                        and self._cont
                    ):
                        workflows.append(wf)
                        resources.append(rc)
                        self._time["step"].append(est_end_time)
                        # self._logger.debug(f"{rc}")
                        for rc_id in rc:
                            self._est_end_times[rc_id] = est_end_time

                self._logger.debug(
                    f"Submitting workflows {workflows} to resources {resources}"
                )
                # There is no need to call the enactor when no new things
                # should happen.
                # self._logger.debug('Adding items: %s, %s', workflows, resources)
                if workflows and resources:
                    self._prof.prof("enactor_submit", uid=self._uid)
                    self._enactor.enact(workflows=workflows)
                    self._prof.prof("enactor_submitted", uid=self._uid)

                    with self._monitor_lock:
                        self._workflows_to_monitor += workflows
                        self._unavail_resources.append(resources)
                    self._logger.debug(
                        "Things monitored: %s, %s, %s",
                        self._workflows_to_monitor,
                        self._unavail_resources,
                        self._est_end_times,
                    )
                # Inform the enactor to continue until everything ends.
                self._prof.prof("enactor_cont", uid=self._uid)
                remain = True
                for workflow in self._campaign["campaign"].workflows:
                    if self._workflows_state[workflow.id] == st.NEW:
                        remain = False
                self._logger.debug(
                    "remain: %s, continue: %s, hold: %s", remain, self._cont, self._hold
                )
                if (remain or self._cont) and not self._hold:
                    self._logger.debug("Let's keep going")
                    # self._enactor.cont()
                    self._cont = False
                    self._hold = True
                    self._logger.debug("Stop execution")
                    sleep(1)
                else:
                    self._logger.debug("Still running on its own")
                self._prof.prof("work_submitted", uid=self._uid)

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
                self._logger.debug(
                    f"Total number of workflows to monitor {len(workflows)}"
                )
                finished = list()
                tmp_start_times = list()
                for i in range(len(workflows)):
                    print(
                        f"Workflows {workflows[i]},",
                        f" to monitor {self._workflows_to_monitor}",
                    )
                    if self._workflows_state[workflows[i].id] in st.CFINAL:
                        resource = self._unavail_resources[i]
                        finished.append((workflows[i], resource))
                        time_now = datetime.now()
                        if time_now == self._est_end_times[resource["id"]]:
                            self._logger.info(
                                "Workflow %s finished at expected time",
                                workflows[i].id,
                            )
                        else:
                            self._logger.debug(
                                "Workflow %s finished %f, expected %f."
                                + "Need to Replanning.",
                                workflows[i].id,
                                time_now,
                                self._est_end_times[resource[0]],
                            )

                            # Creates an array with the expected free time of each
                            # resource. The resource that was just freed will
                            # use the time now.
                            for res in self._resources:
                                if res == resource:
                                    tmp_start_times.append(self._env.now)
                                else:
                                    tmp_start_times.append(
                                        self._est_end_times[res["id"]]
                                    )

                if finished:
                    with self._monitor_lock:
                        for workflow, resource in finished:
                            self._workflows_to_monitor.remove(workflow)
                            self._unavail_resources.remove(resource)

                if tmp_start_times:
                    self._prof.prof("replan_start", uid=self._uid)
                    # Creates an array of the workflows that have not
                    # started executing yet.
                    tmp_campaign = list()
                    for workflow in self._campaign["campaign"].workflows:
                        if self._workflows_state[workflow.id] == st.NEW:
                            tmp_campaign.append(workflow)

                    tmp_num_oper = [workflow["num_oper"] for workflow in tmp_campaign]
                    #                    self._logger.debug('Replanning for: %s, %s, %s',
                    #                                        tmp_start_times,
                    #                                        tmp_campaign,
                    #                                        tmp_num_oper)

                    self._prof.prof("replan_run", uid=self._uid)
                    tmp_plan = self._planner.replan(
                        campaign=tmp_campaign,
                        resources=self._resources,
                        num_oper=tmp_num_oper,
                        start_time=tmp_start_times,
                    )

                    self._prof.prof("replan_done", uid=self._uid)
                    # If the plan has not change means that the last few
                    # workflows are executing, so nothing to plan for and
                    # the enactor should continue running.
                    self._plan = tmp_plan

                    self._update_checkpoints()

                if finished:
                    self._hold = False
                self._prof.prof("workflow_cfinished", uid=self._uid)

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
        if self._hold:
            self._hold = False
        self._prof.prof("monitor_bookkeper_terminate", uid=self._uid)
        if self._monitoring_thread:
            self._monitoring_thread.join()
        self._prof.prof("monitor_bookkeper_terminated", uid=self._uid)
        self._logger.debug("Monitor thread terminated")

        if not self._cont:
            self._cont = True
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
            self._logger.debug(
                "Time now: %s, checkpoints: %s", self._time, self._checkpoints
            )
            while self._checkpoints is None:
                continue

            self._prof.prof("bookkeper_wait", uid=self._uid)
            self._cont = True
            while self._campaign["state"] not in st.CFINAL:
                # if self._time["time"] != self._time["step"][0]:
                #     self._time["time"] = (datetime.now().timestamp() - self._time["globaltime"])
                #     self._cont = True

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
            self._logger.debug(
                "Time now: %s, checkpoint: %s",
                self._time["time"],
                self._checkpoints[-1],
            )
            print(ex)
        finally:
            self.terminate()

    def get_campaign_state(self):

        return self._campaign["state"]

    def get_workflows_state(self):

        states = dict()
        for workflow in self._campaign["campaign"].workflows:
            states[workflow.id] = self._workflows_state[workflow.id]

        return states
