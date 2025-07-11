from unittest import mock

from socm.bookkeeper import Bookkeeper
from socm.workflows import MLMapmakingWorkflow


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
    workflow.resources = {
        "ranks": 1,
        "threads": 32,
        "memory": 80000,
        "runtime": 80000,
    }
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
    bookkeeper._record(workflow)

    # Check that the Slurmise raw_record method was called with the expected job data
    mock_slurmise.raw_record.assert_called_once()
