from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from socm.enactor.rp_enactor import RPEnactor
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
