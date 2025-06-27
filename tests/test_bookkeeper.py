from unittest import mock

from socm.bookkeeper import Bookkeeper
from socm.workflows import MLMapmakingWorkflow


@mock.patch.object(Bookkeeper, "__init__", return_value=None)
@mock.patch("radical.utils.Logger")
def test_record(mocked_logger, mocked_init, mock_slurmise, mock_parse_slurm_job_metadata, mock_context, mock_filemd5):
    """
    Test the record method of the Bookkeeper class.
    """

    workflow = MLMapmakingWorkflow(
        name="ml_mapmaking_workflow",
        executable="so-site-pipeline",
        context="file:///scratch/gpfs/ACT/data/context-so-fixed/context.yaml",
        subcommand="make-ml-map",
        id=1,
        environment={
            "MOBY2_TOD_STAGING_PATH": "/tmp/",
            "DOT_MOBY2": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/act_dot_moby2",
            "SOTODLIB_SITECONFIG": "/scratch/gpfs/SIMONSOBS/users/ip8725/act_test/site.yaml",
        },
        resources={"ranks": 1, "threads": 32, "memory": 80000, "runtime": 80000},
        area="file:///scratch/gpfs/SIMONSOBS/so/science-readiness/footprint/v20250306/so_geometry_v20250306_lat_f090.fits",
        output_dir="/scratch/gpfs/SIMONSOBS/users/ip8725/git/so_mapmaking_campaign_manager/output",
        query="obs_id='1575600533.1575611468.ar5_1'",
        comps="TQU",
        wafers=None,
        bands="f090",
        nmat="corr",
        max_dets=None,
        site="act",
        downsample=1,
        maxiter=10,
        tiled=1,
        wafer="ws0",
    )

    bookkeeper = Bookkeeper()
    bookkeeper._workflows_execids = {1: "1181754.5"}
    bookkeeper._logger = mocked_logger
    bookkeeper._slurmise = mock_slurmise
    bookkeeper._record(workflow)

    # Check that the Slurmise raw_record method was called with the expected job data
    mock_slurmise.raw_record.assert_called_once()
