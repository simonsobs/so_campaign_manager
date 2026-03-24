from unittest import mock

from socm.bookkeeper import Bookkeeper
from socm.core.models import ResourceSpec
from socm.workflows import MLMapmakingWorkflow, SpectraWorkflow


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
