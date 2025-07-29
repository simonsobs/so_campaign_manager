from pathlib import Path

from socm.workflows import PWVNullTestWorkflow
from socm.workflows.ml_null_tests import NullTestWorkflow


def test_pwv_null_test_workflow(mock_context_act, simple_config):
    # breakpoint()
    workflow = PWVNullTestWorkflow(
        **simple_config["campaign"]["ml-null-tests.mission-tests"]
    )
    assert workflow.context == "context.yaml"
    assert workflow.area == "so_geometry_v20250306_lat_f090.fits"
    assert workflow.output_dir == "output/null_tests"
    assert workflow.bands == "f090"
    assert workflow.wafer == "ws0"
    assert workflow.comps == "TQU"
    assert workflow.maxiter == 10
    assert workflow.query == "obs_id IN ('1551468569.1551475843.ar5_1')"
    assert workflow.tiled == 1
    assert workflow.site == "act"
    assert workflow.environment["DOT_MOBY2"] == "act_dot_moby2"
    assert workflow.environment["SOTODLIB_SITECONFIG"] == "site.yaml"
    assert workflow.name == "pwv_null_test_workflow"
    assert workflow.executable == "so-site-pipeline"
    assert workflow.subcommand == "make-ml-map"
    assert workflow.id is None  # Default value for id is None

    workflows = PWVNullTestWorkflow.get_workflows(
        simple_config["campaign"]["ml-null-tests.mission-tests"]
    )
    assert len(workflows) == 4
    print(workflows)
    for idx, workflow in enumerate(workflows):
        assert isinstance(workflow, NullTestWorkflow)
        assert workflow.output_dir == f"output/null_tests/pwv_high_split_{idx + 1}"
        if idx == 0:
            assert workflow.query == "obs_id IN ('1551468569.1551475843.ar5_1')"
            assert workflow.datasize == 259584
        else:
            assert workflow.query == "obs_id IN ()"
            assert workflow.datasize == 0


def test_get_arguments(mock_context_act, simple_config):
    workflows = PWVNullTestWorkflow.get_workflows(
        simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    for idx, workflow in enumerate(workflows):
        assert workflow.get_arguments() == [
            "obs_id IN ('1551468569.1551475843.ar5_1')" if idx == 0 else "obs_id IN ()",
            str(Path("so_geometry_v20250306_lat_f090.fits").absolute()),
            f"output/null_tests/pwv_high_split_{idx + 1}",
            "--bands=f090",
            "--comps=TQU",
            "--context=context.yaml",
            "--maxiter=10",
            "--site=act",
            "--tiled=1",
            "--wafer=ws0",
        ]
