from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from socm.enactor.rp_enactor import RPEnactor
from socm.utils.states import States
from socm.workflows import SATSimWorkflow, ShellScriptWorkflow


@pytest.fixture
def enactor():
    """An RPEnactor without a session or pilot; submitted tasks are captured."""
    enactor = RPEnactor.__new__(RPEnactor)
    enactor._uid = "enactor.test"
    enactor._prof = MagicMock()
    enactor._logger = MagicMock()
    enactor._monitoring_lock = MagicMock()
    enactor._to_monitor = []
    enactor._execution_status = {}
    enactor._callbacks = {}
    enactor._rp_tmgr = MagicMock()
    enactor._monitoring_thread = MagicMock()  # pretend it is running, so enact() does not start one
    return enactor


def _submitted(enactor, workflows):
    """Enact the workflows and return the task descriptions passed to RP."""
    with patch("socm.enactor.rp_enactor.rp.TaskDescription", side_effect=SimpleNamespace):
        enactor.enact(workflows)
    enactor._logger.exception.assert_not_called()
    (tasks,), _ = enactor._rp_tmgr.submit_tasks.call_args
    return tasks


def test_sandbox_under_base_path(enactor):
    workflow = ShellScriptWorkflow(id=3, name="split", script="/s.sh", base_path="/base")
    (task,) = _submitted(enactor, [workflow])
    assert task.sandbox == "/base/split.3"


@pytest.mark.parametrize("base_path", [None, "missing"])
def test_no_base_path_uses_rp_default_sandbox(enactor, base_path):
    kwargs = {} if base_path == "missing" else {"base_path": base_path}
    workflow = ShellScriptWorkflow(id=1, script="/s.sh", **kwargs)
    (task,) = _submitted(enactor, [workflow])
    assert not hasattr(task, "sandbox")


def test_arguments_are_passed_as_a_list(enactor):
    """A string from get_arguments() would be split into single characters by RP."""
    workflow = SATSimWorkflow(id=1, output_dir="out", resources={"ranks": 2, "threads": 1})
    (task,) = _submitted(enactor, [workflow])
    assert task.executable == "toast_so_sim"
    assert task.arguments == workflow.get_arguments()
    assert task.arguments[:3] == ["--out", "out", "--job_group_size=2"]


# ─── _monitor ────────────────────────────────────────────────────────────────

# conftest.py replaces radical.* with mocks, so give the enactor real state names.
FAKE_RP = SimpleNamespace(
    DONE="DONE", FAILED="FAILED", CANCELED="CANCELED", AGENT_EXECUTING="AGENT_EXECUTING",
    FINAL=["DONE", "FAILED", "CANCELED"],
)
FAKE_STATES_MAP = {"DONE": States.DONE, "FAILED": States.FAILED, "CANCELED": States.FAILED}


def _run_monitor_once(enactor, tasks):
    """
    Run one pass of the monitor loop over ``tasks`` ({workflow_id: (rp_state, stdout)})
    and return the callback calls, keyed by their ``new_state``.
    """
    enactor._terminate_monitor = MagicMock()
    enactor._terminate_monitor.is_set.side_effect = [False, True]
    enactor._to_monitor = list(tasks)
    enactor._execution_status = {wid: {} for wid in tasks}
    enactor._rp_tmgr.list_tasks.return_value = [f"workflow.{wid}" for wid in tasks]

    def get_tasks(uids):
        state, stdout = tasks[int(uids.removeprefix("workflow."))]
        return SimpleNamespace(state=state, stdout=stdout)

    enactor._rp_tmgr.get_tasks.side_effect = get_tasks
    callback = MagicMock()
    enactor._callbacks = {"cb": callback}
    with patch("socm.enactor.rp_enactor.rp", FAKE_RP), patch("socm.enactor.rp_enactor.states_map", FAKE_STATES_MAP):
        enactor._monitor()
    return {call.kwargs["new_state"]: call.kwargs for call in callback.call_args_list}


def test_monitor_reports_done_with_step_id(enactor):
    calls = _run_monitor_once(enactor, {1: ("DONE", "output\n1234.5\n")})

    assert set(calls) == {States.DONE}
    assert calls[States.DONE]["workflow_ids"] == [1]
    assert calls[States.DONE]["step_ids"] == ["1234.5"]
    assert enactor._execution_status[1]["state"] == States.DONE
    assert enactor._to_monitor == []


@pytest.mark.parametrize("rp_state", ["FAILED", "CANCELED"])
def test_monitor_reports_failed_and_canceled_as_failed(enactor, rp_state):
    calls = _run_monitor_once(enactor, {1: (rp_state, "")})  # empty stdout must not raise

    assert set(calls) == {States.FAILED}
    assert calls[States.FAILED]["workflow_ids"] == [1]
    assert calls[States.FAILED]["step_ids"] == [None]
    assert enactor._to_monitor == []


def test_monitor_reports_done_and_failed_in_one_pass(enactor):
    calls = _run_monitor_once(enactor, {1: ("DONE", "1234.5"), 2: ("FAILED", ""), 3: ("AGENT_EXECUTING", "")})

    assert calls[States.DONE]["workflow_ids"] == [1]
    assert calls[States.FAILED]["workflow_ids"] == [2]
    assert enactor._to_monitor == [3]   # still running, still monitored


def test_monitor_stops_monitoring_done_workflows_without_failures(enactor):
    """Finished workflows leave the monitoring list even when no workflow failed."""
    _run_monitor_once(enactor, {1: ("DONE", "1234.5"), 2: ("DONE", "1234.6")})

    assert enactor._to_monitor == []
