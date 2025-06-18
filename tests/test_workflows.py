import toml

from socm.workflows import MLMapmakingWorkflow


def test_mlworkflow(simple_toml):

    config = toml.load(simple_toml.toml)
    workflow = MLMapmakingWorkflow(**config["campaign"]["ml-mapmaking"])
    assert workflow.context == "context.yaml"
    assert workflow.area == "so_geometry_v20250306_lat_f090.fits"
    assert workflow.output_dir == "output"
    assert workflow.bands == "f090"
    assert workflow.wafer == "ws0"
    assert workflow.comps == "TQU"
    assert workflow.maxiter == 10
    assert workflow.query == "obs_id='1575600533.1575611468.ar5_1'"
    assert workflow.tiled == 1
    assert workflow.site == "act"
    assert workflow.environment["MOBY2_TOD_STAGING_PATH"] == "/tmp/"
    assert workflow.environment["DOT_MOBY2"] == "act_dot_moby2"
    assert workflow.environment["SOTODLIB_SITECONFIG"] == "site.yaml"
    assert workflow.name == "ml_mapmaking_workflow"
    assert workflow.executable == "so-site-pipeline"
    assert workflow.subcommand == "make-ml-map"
    assert workflow.id is None  # Default value for id is None


def test_get_arguments(simple_toml):
    config = toml.load(simple_toml.toml)
    workflow = MLMapmakingWorkflow(**config["campaign"]["ml-mapmaking"])
    arguments = workflow.get_arguments()
    assert (
        arguments
        == "obs_id='1575600533.1575611468.ar5_1' so_geometry_v20250306_lat_f090.fits output --bands=f090 --comps=TQU --context=context.yaml --maxiter=10 --site=act --tiled=1 --wafer=ws0"
    )


def test_get_command(lite_toml):

    config = toml.load(lite_toml.toml)
    workflow = MLMapmakingWorkflow(**config["campaign"]["ml-mapmaking"])
    command = workflow.get_command(ranks=2)
    expected = "srun --cpu_bind=cores --export=ALL --ntasks-per-node=2 --cpus-per-task=8 so-site-pipeline make-ml-map obs_id='1575600533.1575611468.ar5_1' so_geometry_v20250306_lat_f090.fits output --context=context.yaml --site=act"
    assert command == expected
