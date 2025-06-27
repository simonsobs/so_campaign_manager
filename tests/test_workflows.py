from pathlib import Path

import hypothesis
from hypothesis import given
from hypothesis import strategies as st

from socm.workflows import MLMapmakingWorkflow


def test_mlworkflow(mock_context, simple_config):
    workflow = MLMapmakingWorkflow(**simple_config["campaign"]["ml-mapmaking"])
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


def test_get_arguments(mock_context, simple_config):
    workflow = MLMapmakingWorkflow(**simple_config["campaign"]["ml-mapmaking"])
    arguments = workflow.get_arguments()
    assert (
        arguments
        == f"obs_id='1575600533.1575611468.ar5_1' {Path('so_geometry_v20250306_lat_f090.fits').absolute()} output --bands=f090 --comps=TQU --context=context.yaml --maxiter=10 --site=act --tiled=1 --wafer=ws0"
    )


def test_get_command(mock_context, lite_config):
    workflow = MLMapmakingWorkflow(**lite_config["campaign"]["ml-mapmaking"])
    command = workflow.get_command(ranks=2)
    expected = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node=2 --cpus-per-task=8 so-site-pipeline make-ml-map obs_id='1575600533.1575611468.ar5_1' {Path('so_geometry_v20250306_lat_f090.fits').absolute()} output --context=context.yaml --site=act"
    assert command == expected


@given(
    maxiter=st.one_of(st.integers(), st.lists(st.integers())),
    downsample=st.one_of(st.integers(), st.lists(st.integers())),
    tiled=st.integers(),
    datasize=st.integers(),
)
@hypothesis.settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
def test_get_fields(mock_context, maxiter, downsample, tiled, datasize):
    """
    Test the get_numeric_fields method to ensure it correctly identifies numeric fields.
    """

    config = {
        "context": "context.yaml",
        "area": "area.fits",
        "output_dir": "output",
        "maxiter": maxiter,
        "downsample": downsample,
        "tiled": tiled,
        "datasize": datasize,
    }

    # breakpoint()
    workflow = MLMapmakingWorkflow(**config)
    numeric_fields = workflow.get_numeric_fields()
    assert "maxiter" in numeric_fields
    assert "downsample" in numeric_fields
    assert "tiled" in numeric_fields

    workflow = MLMapmakingWorkflow(**config)
    numeric_fields = workflow.get_numeric_fields(avoid_attributes=["tiled"])
    assert "tiled" not in numeric_fields

    categorical_fields = workflow.get_categorical_fields(avoid_attributes=["executable", "name", "context"])
    assert "subcommand" in categorical_fields
    assert "area" in categorical_fields
    assert "output_dir" in categorical_fields
    assert "query" in categorical_fields
    assert "comps" in categorical_fields
    assert "nmat" in categorical_fields
    assert "site" in categorical_fields
    assert "executable" not in categorical_fields
    assert "name" not in categorical_fields
    assert "context" not in categorical_fields
