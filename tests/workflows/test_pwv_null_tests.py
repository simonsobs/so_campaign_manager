from pathlib import Path

from socm.workflows import PWVNullTestWorkflow
from socm.workflows.ml_null_tests import NullTestWorkflow


def test_pwv_null_test_workflow(mock_context_act, simple_config):
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
    assert len(workflows) == 1
    print(workflows)
    for idx, workflow in enumerate(workflows):
        assert isinstance(workflow, NullTestWorkflow)
        assert workflow.output_dir == f"output/null_tests/pwv_high_split_{idx + 1}"
        assert (
            workflow.query
            == f"file://{str(Path(f'output/null_tests/pwv_high_split_{idx + 1}/query.txt').absolute())}"
        )
        if idx == 0:
            assert workflow.datasize == 259584
        else:
            assert workflow.datasize == 0


def test_get_arguments(mock_context_act, simple_config):
    workflows = PWVNullTestWorkflow.get_workflows(
        simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    for idx, workflow in enumerate(workflows):
        assert workflow.get_arguments() == [
            str(
                Path(f"output/null_tests/pwv_high_split_{idx + 1}/query.txt").absolute()
            ),
            str(Path("so_geometry_v20250306_lat_f090.fits").absolute()),
            f"output/null_tests/pwv_high_split_{idx + 1}",
            str(Path("preprocess.yaml").absolute()),
            "--bands=f090",
            "--comps=TQU",
            "--context=context.yaml",
            "--maxiter=10",
            "--site=act",
            "--tiled=1",
            "--wafer=ws0",
        ]

def test_pwv_null_test_empty_pwv_group(mock_context_act, simple_config, monkeypatch):
    """
    Test that _get_splits handles num_chunks=0 correctly when a PWV group is empty.
    This directly tests the conditional on line 72:
    `obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []`
    """
    config = simple_config["campaign"]["ml-null-tests.mission-tests"].copy()
    workflow = PWVNullTestWorkflow(**config)

    # Create a scenario with empty low PWV observations
    ctx = None  # Mock context not needed for this unit test
    obs_info = {
        "obs1": {"pwv": 3.0, "start_time": 1000},  # High PWV
        "obs2": {"pwv": 3.5, "start_time": 2000},  # High PWV
    }

    splits = workflow._get_splits(ctx, obs_info)

    # Should have high PWV splits
    assert "high" in splits
    assert len(splits["high"]) == workflow.nsplits

    # Low PWV should either be absent or have empty splits
    # (the code skips empty pwv_obs_info with 'continue' on line 65)
    assert "low" not in splits
