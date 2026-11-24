import threading as mt
from unittest import mock
from unittest.mock import MagicMock, patch

import networkx as nx

from socm.bookkeeper import Bookkeeper
from socm.core.models import Batch, PlanEntry, PlanResult, ResourceSpec
from socm.utils.states import States
from socm.workflows import MLMapmakingWorkflow, SpectraWorkflow

# ─── helpers for multi-batch tests ───────────────────────────────────────────

def _wf(wf_id):
    wf = MagicMock()
    wf.id = wf_id
    wf.name = f"wf_{wf_id}"
    wf.depends = []
    return wf


def _entry(wf, start, end):
    return PlanEntry(workflow=wf, cores=range(2), memory=1000.0,
                     start_time=float(start), end_time=float(end))


def _batch(plan, node_ids):
    g = nx.DiGraph()
    for nid in node_ids:
        g.add_node(nid)
    return Batch(plan=plan, graph=g)


def _make_bk(batches, objective=100.0):
    """Bypass __init__ and wire up the minimal state needed for unit tests."""
    bk = Bookkeeper.__new__(Bookkeeper)
    bk._uid = "bookkeeper.test"
    bk._logger = MagicMock()
    bk._prof = MagicMock()
    # Use real RLocks so that concurrent callback calls work correctly.
    bk._exec_state_lock = mt.RLock()
    bk._monitor_lock = mt.RLock()
    bk._terminate_event = mt.Event()
    bk._batch_finished = mt.Event()
    bk._planning_done = mt.Event()
    bk._current_batch_wf_ids = set()
    bk._checkpoints = None
    bk._objective = objective
    bk._workflows_state = {}
    bk._workflows_to_monitor = []
    bk._unavail_resources = []
    bk._est_end_times = {}
    campaign = MagicMock()
    campaign.execution_schema = "batch"
    bk._campaign = {"campaign": campaign, "state": States.NEW}
    bk._resource = MagicMock()
    bk._resource.memory_per_node = 1000.0
    bk._resource.cores_per_node = 4
    bk._dryrun = True
    bk._plan_result = PlanResult(qos=None, ncores=2, batches=batches)
    bk._enactor = MagicMock()
    # Populate workflow states for every workflow that appears in any batch graph.
    for batch in batches:
        for node_id in batch.graph.nodes():
            bk._workflows_state[node_id] = States.NEW
    return bk


@mock.patch.object(Bookkeeper, "__init__", return_value=None)
@mock.patch("radical.utils.Logger")
def test_record(mocked_logger, mocked_init, mock_slurmise, mock_parse_slurm_job_metadata, mock_context, mock_filemd5):
    """
    Test the record method of the Bookkeeper class.
    """

    workflow = mock.MagicMock(spec=MLMapmakingWorkflow)
    workflow.name = "ml_mapmaking_workflow"
    workflow.executable = "so-site-pipeline"
    workflow.context = "file:///scratch/gpfs/ACT/data/context-so-fixed/context.yaml"
    workflow.subcommand = "make-ml-map"
    workflow.id = 1
    workflow.environment = {
        "MOBY2_TOD_STAGING_PATH": "/tmp/",
        "DOT_MOBY2": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/act_dot_moby2",
        "SOTODLIB_SITECONFIG": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/site.yaml",
    }
    workflow.resources = ResourceSpec(ranks=1, threads=32, memory=80000, runtime=80000)
    workflow.area = (
        "file:///scratch/gpfs/SIMONSOBS/so/science-readiness/footprint/v20250306/so_geometry_v20250306_lat_f090.fits"
    )
    workflow.output_dir = "/scratch/gpfs/SIMONSOBS/users/ip8725/git/so_mapmaking_campaign_manager/output"
    workflow.query = "obs_id='1575600533.1575611468.ar5_1'"
    workflow.comps = "TQU"
    workflow.wafers = None
    workflow.bands = "f090"
    workflow.nmat = "corr"
    workflow.max_dets = None
    workflow.site = "act"
    workflow.downsample = 1
    workflow.maxiter = 10
    workflow.tiled = 1
    workflow.wafer = "ws0"

    bookkeeper = Bookkeeper()
    bookkeeper._workflows_execids = {1: "1181754.5"}
    bookkeeper._logger = mocked_logger
    bookkeeper._slurmise = mock_slurmise
    bookkeeper._dryrun = False
    bookkeeper._record(workflow)

    # Check that the Slurmise raw_record method was called with the expected job data
    mock_slurmise.raw_record.assert_called_once()


@mock.patch.object(Bookkeeper, "__init__", return_value=None)
@mock.patch("radical.utils.Logger")
def test_record_dryrun(mocked_logger, mocked_init, mock_slurmise, mock_parse_slurm_job_metadata, mock_context, mock_filemd5):
    """
    Test the record method of the Bookkeeper class.
    """

    workflow = mock.MagicMock(spec=MLMapmakingWorkflow)
    workflow.name = "ml_mapmaking_workflow"
    workflow.executable = "so-site-pipeline"
    workflow.context = "file:///scratch/gpfs/ACT/data/context-so-fixed/context.yaml"
    workflow.subcommand = "make-ml-map"
    workflow.id = 1
    workflow.environment = {
        "MOBY2_TOD_STAGING_PATH": "/tmp/",
        "DOT_MOBY2": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/act_dot_moby2",
        "SOTODLIB_SITECONFIG": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/site.yaml",
    }
    workflow.resources = ResourceSpec(ranks=1, threads=32, memory=80000, runtime=80000)
    workflow.area = (
        "file:///scratch/gpfs/SIMONSOBS/so/science-readiness/footprint/v20250306/so_geometry_v20250306_lat_f090.fits"
    )
    workflow.output_dir = "/scratch/gpfs/SIMONSOBS/users/ip8725/git/so_mapmaking_campaign_manager/output"
    workflow.query = "obs_id='1575600533.1575611468.ar5_1'"
    workflow.comps = "TQU"
    workflow.wafers = None
    workflow.bands = "f090"
    workflow.nmat = "corr"
    workflow.max_dets = None
    workflow.site = "act"
    workflow.downsample = 1
    workflow.maxiter = 10
    workflow.tiled = 1
    workflow.wafer = "ws0"

    bookkeeper = Bookkeeper()
    bookkeeper._workflows_execids = {1: "1181754.5"}
    bookkeeper._logger = mocked_logger
    bookkeeper._slurmise = mock_slurmise
    bookkeeper._dryrun = True
    bookkeeper._record(workflow)

    # Check that the Slurmise raw_record method was called with the expected job data
    mock_slurmise.raw_record.assert_not_called()


@mock.patch.object(Bookkeeper, "__init__", return_value=None)
@mock.patch("radical.utils.Logger")
def test_record_list_categorical_field(mocked_logger, mocked_init, mock_slurmise, mock_parse_slurm_job_metadata, mock_filemd5):
    """
    Test that list-valued categorical fields are expanded into indexed keys
    (e.g. script_args_0, script_args_1) rather than stored as a single entry.
    """
    workflow = mock.MagicMock(spec=SpectraWorkflow)
    workflow.id = 1
    workflow.name = "pspipe_workflow"
    workflow.resources = ResourceSpec(ranks=4, threads=2, memory=80000, runtime=60)
    workflow.script_args = ["plain_arg", "file:///some/path.fits"]
    workflow.subcommand = "script.py"
    workflow.get_numeric_fields.return_value = []
    workflow.get_categorical_fields.return_value = ["script_args", "subcommand"]
    workflow.get_command.return_value = "srun ... python -u script.py"

    bookkeeper = Bookkeeper()
    bookkeeper._workflows_execids = {1: "1181754.5"}
    bookkeeper._logger = mocked_logger
    bookkeeper._slurmise = mock_slurmise
    bookkeeper._dryrun = False

    with mock.patch("socm.bookkeeper.bookkeeper.JobData") as mock_jobdata:
        bookkeeper._record(workflow)
        categorical = mock_jobdata.call_args.kwargs["categorical"]

    assert "script_args" not in categorical
    assert categorical["script_args_0"] == "plain_arg"
    assert categorical["script_args_1"] == "efca7302276bceac49b8326a7b88f008"  # FileMD5 mock value
    assert categorical["subcommand"] == "script.py"


@mock.patch.object(Bookkeeper, "__init__", return_value=None)
@mock.patch("radical.utils.Logger")
def test_record_excludes_depends_from_categorical(mocked_logger, mocked_init, mock_slurmise, mock_parse_slurm_job_metadata, mock_filemd5):
    """
    Test that 'depends' is included in avoid_attributes so workflow dependencies
    never appear in the categorical fields passed to Slurmise.
    """
    workflow = mock.MagicMock(spec=MLMapmakingWorkflow)
    workflow.id = 1
    workflow.name = "ml_mapmaking_workflow"
    workflow.resources = ResourceSpec(ranks=1, threads=32, memory=80000, runtime=80000)
    workflow.depends = ["other_workflow"]
    workflow.get_numeric_fields.return_value = []
    workflow.get_categorical_fields.return_value = []
    workflow.get_command.return_value = "srun ..."

    bookkeeper = Bookkeeper()
    bookkeeper._workflows_execids = {1: "1181754.5"}
    bookkeeper._logger = mocked_logger
    bookkeeper._slurmise = mock_slurmise
    bookkeeper._dryrun = False
    bookkeeper._record(workflow)

    workflow.get_categorical_fields.assert_called_once_with(
        avoid_attributes=["executable", "name", "context", "output_dir", "query", "depends"]
    )


# ─── _update_checkpoints ─────────────────────────────────────────────────────

def test_update_checkpoints_basic():
    bk = _make_bk(batches=[])
    wf = _wf(1)
    bk._update_checkpoints([_entry(wf, 10.0, 40.0), _entry(wf, 50.0, 80.0)])
    assert bk._checkpoints == [0, 10.0, 40.0, 50.0, 80.0]


def test_update_checkpoints_deduplicates_shared_boundary():
    bk = _make_bk(batches=[])
    wf = _wf(1)
    bk._update_checkpoints([_entry(wf, 0.0, 30.0), _entry(wf, 30.0, 60.0)])
    assert bk._checkpoints == [0, 30.0, 60.0]


# ─── _verify_objective ───────────────────────────────────────────────────────

def test_verify_objective_passes_when_makespan_within_deadline():
    wf = _wf(1)
    batch = _batch([_entry(wf, 0, 50)], [1])
    bk = _make_bk([batch], objective=100.0)
    assert bk._verify_objective() is True


def test_verify_objective_fails_when_makespan_exceeds_deadline():
    wf = _wf(1)
    batch = _batch([_entry(wf, 0, 150)], [1])
    bk = _make_bk([batch], objective=100.0)
    assert bk._verify_objective() is False


# ─── state_update_cb ─────────────────────────────────────────────────────────

def test_state_update_cb_sets_batch_finished_when_all_done():
    bk = _make_bk(batches=[])
    bk._current_batch_wf_ids = {1, 2}
    bk._workflows_state = {1: States.NEW, 2: States.NEW}

    bk.state_update_cb(workflow_ids=[1, 2], new_state=States.DONE)

    assert bk._batch_finished.is_set()


def test_state_update_cb_no_batch_finished_when_partial():
    bk = _make_bk(batches=[])
    bk._current_batch_wf_ids = {1, 2}
    bk._workflows_state = {1: States.NEW, 2: States.NEW}

    bk.state_update_cb(workflow_ids=[1], new_state=States.DONE)

    assert not bk._batch_finished.is_set()


def test_state_update_cb_no_batch_finished_when_no_current_batch():
    bk = _make_bk(batches=[])
    bk._current_batch_wf_ids = set()
    bk._workflows_state = {1: States.NEW}

    bk.state_update_cb(workflow_ids=[1], new_state=States.DONE)

    assert not bk._batch_finished.is_set()


# ─── work() ──────────────────────────────────────────────────────────────────

@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_single_batch_setup_and_teardown(mock_sleep):
    wf1 = _wf(1)
    plan = [_entry(wf1, 0, 50)]
    bk = _make_bk([_batch(plan, [1])], objective=100.0)

    def mock_enact(workflows):
        bk.state_update_cb(workflow_ids=[w.id for w in workflows], new_state=States.DONE)
    bk._enactor.enact.side_effect = mock_enact

    bk.work()

    assert bk._planning_done.is_set()
    bk._enactor.setup.assert_called_once()
    bk._enactor.teardown.assert_called_once()


@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_multi_batch_setup_and_teardown_per_batch(mock_sleep):
    # Use the full sorted plan in both batches so plan[wf_id-1] indexing works.
    wf1, wf2 = _wf(1), _wf(2)
    full_plan = [_entry(wf1, 0, 30), _entry(wf2, 30, 60)]
    bk = _make_bk([_batch(full_plan, [1]), _batch(full_plan, [2])], objective=100.0)

    def mock_enact(workflows):
        bk.state_update_cb(workflow_ids=[w.id for w in workflows], new_state=States.DONE)
    bk._enactor.enact.side_effect = mock_enact

    bk.work()

    assert bk._enactor.setup.call_count == 2
    assert bk._enactor.teardown.call_count == 2
    assert bk._planning_done.is_set()


@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_failed_objective_sets_planning_done_and_no_setup(mock_sleep):
    wf1 = _wf(1)
    plan = [_entry(wf1, 0, 200)]  # makespan exceeds objective of 100
    bk = _make_bk([_batch(plan, [1])], objective=100.0)

    bk.work()

    assert bk._planning_done.is_set()
    assert bk._campaign["state"] == States.FAILED
    bk._enactor.setup.assert_not_called()
    bk._enactor.teardown.assert_not_called()


@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_terminate_event_skips_teardown(mock_sleep):
    wf1 = _wf(1)
    plan = [_entry(wf1, 0, 50)]
    bk = _make_bk([_batch(plan, [1])], objective=100.0)

    def mock_enact(workflows):
        bk._terminate_event.set()
    bk._enactor.enact.side_effect = mock_enact

    bk.work()

    bk._enactor.teardown.assert_not_called()


# ─── failed workflows ────────────────────────────────────────────────────────

def _chain_batch(plan):
    """A batch where workflow 2 depends on workflow 1."""
    batch = _batch(plan, [1, 2])
    batch.graph.add_edge(1, 2)
    return batch


@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_does_not_enact_children_of_a_failed_workflow(mock_sleep):
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([_chain_batch([_entry(wf1, 0, 30), _entry(wf2, 30, 60)])])

    def mock_enact(workflows):
        bk.state_update_cb(workflow_ids=[w.id for w in workflows], new_state=States.FAILED)
    bk._enactor.enact.side_effect = mock_enact
    # The child stays NEW, so the batch never finishes; stop after a few polls.
    mock_sleep.side_effect = lambda _: mock_sleep.call_count >= 3 and bk._terminate_event.set()

    bk.work()

    bk._enactor.enact.assert_called_once_with(workflows=[wf1])
    assert bk._workflows_state == {1: States.FAILED, 2: States.NEW}


@patch("socm.bookkeeper.bookkeeper.sleep")
def test_work_enacts_children_of_a_done_workflow(mock_sleep):
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([_chain_batch([_entry(wf1, 0, 30), _entry(wf2, 30, 60)])])

    def mock_enact(workflows):
        bk.state_update_cb(workflow_ids=[w.id for w in workflows], new_state=States.DONE)
    bk._enactor.enact.side_effect = mock_enact

    bk.work()

    assert [c.kwargs["workflows"] for c in bk._enactor.enact.call_args_list] == [[wf1], [wf2]]


def test_run_ends_failed_when_a_workflow_fails():
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([])
    bk._campaign["campaign"].workflows = [wf1, wf2]
    bk.terminate = MagicMock()
    bk.monitor = MagicMock()

    def work():
        bk.state_update_cb(workflow_ids=[1], new_state=States.FAILED)
        bk._planning_done.set()
    bk.work = work

    bk.run()

    assert bk.get_campaign_state() == States.FAILED
    bk.terminate.assert_called_once()


def test_monitor_does_not_record_failed_workflows():
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([])
    bk._workflows_state = {1: States.DONE, 2: States.FAILED}
    bk._workflows_to_monitor = [wf1, wf2]
    bk._unavail_resources = [(range(2), 1), (range(2), 1)]
    bk._record = MagicMock()

    thread = mt.Thread(target=bk.monitor)
    thread.start()
    for _ in range(500):
        if not bk._workflows_to_monitor:
            break
        mt.Event().wait(0.01)
    bk._terminate_event.set()
    thread.join(timeout=5)

    assert bk._workflows_to_monitor == []
    bk._record.assert_called_once_with(wf1)


@patch("socm.bookkeeper.bookkeeper.sleep", lambda _: mt.Event().wait(0.01))
def test_shutdown_does_not_hang_with_a_failed_workflow_and_a_running_sibling():
    """
    The enactor stops reporting states on terminate(), so a sibling that is still
    running never reaches a final state. Shutdown must not wait for it.
    """
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([])
    bk._campaign["campaign"].workflows = [wf1, wf2]

    def work():
        with bk._monitor_lock:
            bk._workflows_to_monitor += [wf1, wf2]
            bk._unavail_resources += [(range(2), 1), (range(2), 1)]
        bk.state_update_cb(workflow_ids=[2], new_state=States.EXECUTING)
        bk.state_update_cb(workflow_ids=[1], new_state=States.FAILED)
        bk._planning_done.set()
    bk.work = work

    runner = mt.Thread(target=bk.run, daemon=True)
    runner.start()
    runner.join(timeout=5)
    hung = runner.is_alive()
    if hung:
        # Let a stuck monitor thread exit, so it does not block the test session.
        with bk._monitor_lock:
            bk._workflows_to_monitor.clear()
        runner.join(timeout=5)

    assert not hung, "Bookkeeper.run() did not return after a workflow failed"
    assert bk.get_campaign_state() == States.FAILED
    assert bk._workflows_state[2] == States.EXECUTING
    bk._enactor.terminate.assert_called_once()
    assert not bk._monitoring_thread.is_alive()


def test_monitor_records_workflows_that_finished_during_shutdown():
    """
    A workflow that finished just before shutdown is still recorded and released;
    a sibling that is still executing is not waited for.
    """
    wf1, wf2 = _wf(1), _wf(2)
    bk = _make_bk([])
    bk._workflows_state = {1: States.DONE, 2: States.EXECUTING}
    bk._workflows_to_monitor = [wf1, wf2]
    bk._unavail_resources = [(range(2), 1), (range(2, 4), 1)]
    bk._record = MagicMock()
    bk._terminate_event.set()   # shutdown started before the monitor's next pass

    thread = mt.Thread(target=bk.monitor, daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
    bk._record.assert_called_once_with(wf1)
    assert bk._workflows_to_monitor == [wf2]
    assert bk._unavail_resources == [(range(2, 4), 1)]
