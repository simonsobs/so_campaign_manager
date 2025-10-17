"""Tests for socm.enactor.dryrun_enactor module."""

import os
import time
from datetime import datetime
from threading import Event
from unittest import mock
from unittest.mock import MagicMock, Mock, patch

import pytest

from socm.core.models import Resource, Workflow
from socm.enactor.dryrun_enactor import DryrunEnactor
from socm.utils.states import States


@pytest.fixture
def sample_workflows():
    """Create sample workflow objects for testing."""
    workflows = []
    for i in range(3):
        workflow = Mock(spec=Workflow)
        workflow.id = f"workflow.{i}"
        workflow.name = f"test_workflow_{i}"
        workflow.resources = {"ranks": 1, "threads": 8}
        workflows.append(workflow)
    return workflows


@pytest.fixture
def sample_resource():
    """Create a sample resource for testing."""
    return Resource(
        name="test_resource",
        nodes=4,
        cores_per_node=112,
        memory_per_node=64000,
    )


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_init_creates_required_attributes(mocked_profiler, mocked_logger):
    """Test that __init__ creates all required attributes."""

    enactor = DryrunEnactor(sid="test_session")

    # Verify attributes exist
    assert hasattr(enactor, "_to_monitor")
    assert isinstance(enactor._to_monitor, list)
    assert len(enactor._to_monitor) == 0

    assert hasattr(enactor, "_monitoring_lock")
    assert hasattr(enactor, "_cb_lock")
    assert hasattr(enactor, "_callbacks")
    assert isinstance(enactor._callbacks, dict)

    assert hasattr(enactor, "_monitoring_thread")
    assert enactor._monitoring_thread is None

    assert hasattr(enactor, "_terminate_monitor")
    assert isinstance(enactor._terminate_monitor, Event)

    assert enactor._run is False
    assert enactor._resource is None


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_init_sets_radical_config(mocked_profiler, mocked_logger):
    """Test that __init__ sets RADICAL_CONFIG_USER_DIR environment variable."""

    _ = DryrunEnactor(sid="test_session")

    # Verify environment variable was set
    assert "RADICAL_CONFIG_USER_DIR" in os.environ
    assert "configs" in os.environ["RADICAL_CONFIG_USER_DIR"]


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_setup_stores_resource(mocked_profiler, mocked_logger, sample_resource):
    """Test that setup() stores the resource."""

    enactor = DryrunEnactor(sid="test_session")
    enactor.setup(resource=sample_resource, walltime=3600, cores=112)

    assert enactor._resource == sample_resource

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_enact_single_workflow(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test enacting a single workflow."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    enactor.enact([workflow])

    # Verify workflow was added to monitoring list
    assert workflow.id in enactor._to_monitor

    # Verify workflow status was set
    assert workflow.id in enactor._execution_status
    assert enactor._execution_status[workflow.id]["state"] == States.EXECUTING
    assert enactor._execution_status[workflow.id]["exec_thread"] is None
    assert isinstance(enactor._execution_status[workflow.id]["start_time"], datetime)
    assert enactor._execution_status[workflow.id]["end_time"] is None

    # Verify monitoring thread was created and started
    assert enactor._monitoring_thread is not None
    mocked_thread.assert_called_once_with(target=enactor._monitor, name="monitor-thread")
    mock_thread_instance.start.assert_called_once()

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_enact_multiple_workflows(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test enacting multiple workflows."""

    enactor = DryrunEnactor(sid="test_session")

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance
    enactor.enact(sample_workflows)

    # Verify all workflows were added to monitoring list
    for workflow in sample_workflows:
        assert workflow.id in enactor._to_monitor
        assert workflow.id in enactor._execution_status
        assert enactor._execution_status[workflow.id]["state"] == States.EXECUTING


    assert enactor._monitoring_thread is not None
    mocked_thread.assert_called_once_with(target=enactor._monitor, name="monitor-thread")
    mock_thread_instance.start.assert_called_once()

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_enact_duplicate_workflow(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test that enacting the same workflow twice logs a warning."""

    enactor = DryrunEnactor(sid="test_session")

    workflow = sample_workflows[0]

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    # Enact workflow first time
    enactor.enact([workflow])
    initial_count = len(enactor._to_monitor)

    # Enact same workflow again
    enactor.enact([workflow])

    # Verify workflow was not added again
    assert len(enactor._to_monitor) == initial_count

    # Verify warning was logged (access the logger instance via return_value)
    mocked_logger.return_value.info.assert_any_call(
        "Workflow %s is in state %s",
        workflow,
        States.EXECUTING.name,
    )

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_enact_with_callback(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test that enact calls registered callbacks."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    # Register a callback
    callback = Mock()
    callback.__name__ = "test_callback"
    enactor.register_state_cb(callback)

    enactor.enact([workflow])

    # Verify callback was called with EXECUTING state
    callback.assert_called_once_with(
        workflow_ids=[workflow.id],
        new_state=States.EXECUTING,
        step_ids=[None],
    )

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_enact_profiling_events(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test that enact logs profiling events."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance
    enactor.enact([workflow])

    # Verify profiling events were logged
    mocked_profiler.return_value.prof.assert_any_call("enacting_start", uid=enactor._uid)
    mocked_profiler.return_value.prof.assert_any_call("enacting_stop", uid=enactor._uid)

    # Cleanup
    enactor.terminate()



@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_monitor_completes_workflows(mocked_profiler, mocked_logger, sample_workflows):
    """Test that monitor thread transitions workflows to DONE state."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    enactor.enact([workflow])

    # Wait for monitoring to complete the workflow
    time.sleep(2)

    # Verify workflow was marked as DONE
    assert enactor._execution_status[workflow.id]["state"] == States.DONE
    assert enactor._execution_status[workflow.id]["end_time"] is not None
    assert workflow.id not in enactor._to_monitor

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_monitor_calls_callbacks_on_completion(mocked_profiler, mocked_logger, sample_workflows):
    """Test that monitor calls callbacks when workflows complete."""\

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Register a callback
    callback = Mock()
    callback.__name__ = "test_callback"
    enactor.register_state_cb(callback)

    enactor.enact([workflow])

    # Wait for monitoring to complete
    time.sleep(2)

    # Verify callback was called with DONE state
    # Note: callback will be called twice - once for EXECUTING, once for DONE
    assert callback.call_count >= 2
    done_calls = [call for call in callback.call_args_list
                    if call[1].get("new_state") == States.DONE]
    assert len(done_calls) > 0

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_monitor_handles_multiple_workflows(mocked_profiler, mocked_logger, sample_workflows):
    """Test that monitor can handle multiple workflows simultaneously."""

    enactor = DryrunEnactor(sid="test_session")

    enactor.enact(sample_workflows)

    # Wait for all workflows to complete
    time.sleep(3)

    # Verify all workflows were completed
    for workflow in sample_workflows:
        assert enactor._execution_status[workflow.id]["state"] == States.DONE
        assert workflow.id not in enactor._to_monitor

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_monitor_profiling_events(mocked_profiler, mocked_logger, sample_workflows):
    """Test that monitor logs profiling events."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    enactor.enact([workflow])

    # Wait for monitoring to complete
    time.sleep(2)

    # Verify profiling events were logged
    mocked_profiler.return_value.prof.assert_any_call("workflow_monitor_start", uid=enactor._uid)
    mocked_profiler.return_value.prof.assert_any_call("workflow_success", uid=enactor._uid)
    mocked_profiler.return_value.prof.assert_any_call("workflow_monitor_end", uid=enactor._uid)

    # Cleanup
    enactor.terminate()


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_get_status_no_arguments(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test get_status() with no arguments returns all workflow statuses."""

    enactor = DryrunEnactor(sid="test_session")

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    enactor.enact(sample_workflows)

    status = enactor.get_status()

    # Verify all workflows are in the status dict
    assert len(status) == len(sample_workflows)
    for workflow in sample_workflows:
        assert workflow.id in status
        assert status[workflow.id] == States.EXECUTING

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_get_status_single_workflow(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test get_status() with a single workflow ID."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    enactor.enact([workflow])

    status = enactor.get_status(workflows=workflow.id)

    # Verify status dict contains only the requested workflow
    assert len(status) == 1
    assert workflow.id in status
    assert status[workflow.id] == States.EXECUTING

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
@mock.patch("threading.Thread")
def test_get_status_list_of_workflows(mocked_thread, mocked_profiler, mocked_logger, sample_workflows):
    """Test get_status() with a list of workflow IDs."""

    enactor = DryrunEnactor(sid="test_session")

    # Mock the monitoring thread to prevent it from actually running
    mock_thread_instance = MagicMock()
    mocked_thread.return_value = mock_thread_instance

    enactor.enact(sample_workflows)

    workflow_ids = [workflow.id for workflow in sample_workflows[:2]]
    status = enactor.get_status(workflows=workflow_ids)

    # Verify status dict contains only the requested workflows
    assert len(status) == 2
    for workflow_id in workflow_ids:
        assert workflow_id in status
        assert status[workflow_id] == States.EXECUTING

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_update_status(mocked_profiler, mocked_logger, sample_workflows):
    """Test update_status() changes workflow state."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]
    enactor.enact([workflow])

    # Update status
    enactor.update_status(workflow.id, States.FAILED)

    # Verify status was updated
    assert enactor._execution_status[workflow.id]["state"] == States.FAILED

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_update_status_non_existent_workflow(mocked_profiler, mocked_logger):
    """Test update_status() logs warning for non-existent workflow."""

    enactor = DryrunEnactor(sid="test_session")

    # Try to update status of non-existent workflow
    enactor.update_status("non_existent_workflow", States.FAILED)

    # Verify warning was logged
    mocked_logger.return_value.warning.assert_called_once()

    # Cleanup
    enactor.terminate()


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_register_state_cb(mocked_profiler, mocked_logger):
    """Test registering a state callback."""

    enactor = DryrunEnactor(sid="test_session")

    # Register callback
    callback = Mock()
    callback.__name__ = "test_callback"
    enactor.register_state_cb(callback)

    # Verify callback was registered
    assert "test_callback" in enactor._callbacks
    assert enactor._callbacks["test_callback"] == callback

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_register_multiple_callbacks(mocked_profiler, mocked_logger):
    """Test registering multiple callbacks."""

    enactor = DryrunEnactor(sid="test_session")

    # Register multiple callbacks
    callback1 = Mock()
    callback1.__name__ = "callback1"
    callback2 = Mock()
    callback2.__name__ = "callback2"

    enactor.register_state_cb(callback1)
    enactor.register_state_cb(callback2)

    # Verify both callbacks were registered
    assert len(enactor._callbacks) == 2
    assert "callback1" in enactor._callbacks
    assert "callback2" in enactor._callbacks

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_callbacks_are_thread_safe(mocked_profiler, mocked_logger, sample_workflows):
    """Test that callback registration uses locking."""

    enactor = DryrunEnactor(sid="test_session")

    # Verify _cb_lock was created
    assert hasattr(enactor, "_cb_lock")

    # Register callback - should use the lock
    callback = Mock()
    callback.__name__ = "test_callback"
    enactor.register_state_cb(callback)

    # No exception should be raised
    assert "test_callback" in enactor._callbacks


@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_terminate_stops_monitoring_thread(mocked_profiler, mocked_logger, sample_workflows):
    """Test that terminate() stops the monitoring thread."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]
    enactor.enact([workflow])

    # Verify monitoring thread is running
    assert enactor._monitoring_thread is not None
    assert enactor._monitoring_thread.is_alive()

    # Terminate enactor
    enactor.terminate()

    # Give thread time to terminate
    time.sleep(0.5)

    # Verify monitoring thread has stopped
    assert not enactor._monitoring_thread.is_alive()
    assert enactor._terminate_monitor.is_set()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_terminate_logs_profiling_events(mocked_profiler, mocked_logger, sample_workflows):
    """Test that terminate() logs profiling events."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]
    enactor.enact([workflow])

    enactor.terminate()

    # Verify profiling events were logged
    mocked_profiler.return_value.prof.assert_any_call("str_terminating", uid=enactor._uid)
    mocked_profiler.return_value.prof.assert_any_call("monitor_terminate", uid=enactor._uid)
    mocked_profiler.return_value.prof.assert_any_call("monitor_terminated", uid=enactor._uid)

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_terminate_without_monitoring_thread(mocked_profiler, mocked_logger):
    """Test that terminate() works when no monitoring thread exists."""

    enactor = DryrunEnactor(sid="test_session")

    # Terminate without starting any workflows
    enactor.terminate()

    # Should not raise any exceptions
    mocked_logger.return_value.info.assert_called_with("Start terminating procedure")



@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_enact_with_exception(mocked_profiler, mocked_logger, sample_workflows):
    """Test that enact handles exceptions gracefully."""

    enactor = DryrunEnactor(sid="test_session")
    workflow = sample_workflows[0]

    # Mock monitoring lock to raise an exception
    with patch.object(enactor, "_monitoring_lock") as mock_lock:
        mock_lock.__enter__ = Mock(side_effect=Exception("Test exception"))
        mock_lock.__exit__ = Mock()

        # Enact should handle the exception
        enactor.enact([workflow])

        # Verify error was logged
        mocked_logger.return_value.error.assert_called()

    # Cleanup
    if enactor._monitoring_thread and enactor._monitoring_thread.is_alive():
        enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_concurrent_enact_calls(mocked_profiler, mocked_logger, sample_workflows):
    """Test that multiple enact calls work correctly."""

    enactor = DryrunEnactor(sid="test_session")

    # Enact workflows in separate calls
    enactor.enact([sample_workflows[0]])
    enactor.enact([sample_workflows[1]])
    enactor.enact([sample_workflows[2]])

    # Verify all workflows are being monitored
    for workflow in sample_workflows:
        assert workflow.id in enactor._execution_status

    # Verify only one monitoring thread exists
    assert enactor._monitoring_thread is not None

    # Cleanup
    enactor.terminate()

@mock.patch("radical.utils.Logger")
@mock.patch("radical.utils.Profiler")
def test_monitoring_with_empty_list(mocked_profiler, mocked_logger):
    """Test that monitoring handles empty workflow list gracefully."""

    enactor = DryrunEnactor(sid="test_session")

    # Enact with empty list should not crash
    enactor.enact([])

    # Monitoring thread should not start for empty list
    # Wait a bit to ensure no thread was started
    time.sleep(0.5)

    # No monitoring thread should exist
    assert enactor._monitoring_thread is None
