from socm.workflows.ml_null_tests import NullTestWorkflow


def test_null_test_workflow_initialization(mock_context_act, simple_config):
    """Test basic initialization of NullTestWorkflow."""
    workflow = NullTestWorkflow(
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
    assert workflow.name == "lat_null_test_workflow"
    assert workflow.executable == "so-site-pipeline"
    assert workflow.subcommand == "make-ml-map"
    assert workflow.id is None
    assert workflow.chunk_nobs == 5
    assert workflow.chunk_duration is None
    assert workflow.datasize == 259584


def test_null_test_workflow_get_num_chunks_normal(mock_context_act, simple_config):
    """Test _get_num_chunks with normal observation counts."""
    workflow = NullTestWorkflow(
        **simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    # Test with various observation counts
    assert workflow._get_num_chunks(5) == 1  # Exactly chunk_nobs
    assert workflow._get_num_chunks(10) == 2  # 2 * chunk_nobs
    assert workflow._get_num_chunks(7) == 2  # Ceiling division: (7+5-1)//5 = 2
    assert workflow._get_num_chunks(11) == 3  # Ceiling division: (11+5-1)//5 = 3
    assert workflow._get_num_chunks(1) == 1  # Less than chunk_nobs


def test_null_test_workflow_get_num_chunks_zero(mock_context_act, simple_config):
    """
    Test _get_num_chunks when num_obs is 0.

    This is a critical edge case that occurs when a split category has no
    observations (e.g., all observations are 'high' PWV, leaving 'low' empty).
    """
    workflow = NullTestWorkflow(
        **simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    # When num_obs is 0, num_chunks should be 0
    assert workflow._get_num_chunks(0) == 0


def test_null_test_workflow_get_arguments(mock_context_act, simple_config):
    """Test get_arguments method returns properly formatted argument list."""
    workflow = NullTestWorkflow(
        **simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    arguments = workflow.get_arguments()

    # Check that the first 4 arguments are paths in correct order
    assert len(arguments) >= 4
    assert "obs_id IN ('1551468569.1551475843.ar5_1')" in arguments[0]
    assert "so_geometry_v20250306_lat_f090.fits" in arguments[1]
    assert arguments[2] == "output/null_tests"
    assert "preprocess.yaml" in arguments[3]

    # Check that optional arguments are formatted correctly with --key=value
    assert "--bands=f090" in arguments
    assert "--comps=TQU" in arguments
    assert "--context=context.yaml" in arguments
    assert "--maxiter=10" in arguments
    assert "--site=act" in arguments
    assert "--tiled=1" in arguments
    assert "--wafer=ws0" in arguments


def test_null_test_workflow_get_arguments_excludes_internal_fields(
    mock_context_act, simple_config
):
    """Test that get_arguments excludes internal workflow fields."""
    workflow = NullTestWorkflow(
        **simple_config["campaign"]["ml-null-tests.mission-tests"]
    )

    arguments = workflow.get_arguments()
    arg_string = " ".join(arguments)

    # These fields should not appear in arguments
    assert "--executable=" not in arg_string
    assert "--subcommand=" not in arg_string
    assert "--id=" not in arg_string
    assert "--environment=" not in arg_string
    assert "--resources=" not in arg_string
    assert "--datasize=" not in arg_string
    assert "--chunk_nobs=" not in arg_string
    assert "--nsplits=" not in arg_string
    assert "--name=" not in arg_string
    assert "--chunk_duration=" not in arg_string


def test_null_test_workflow_with_file_query(mock_context_act, simple_config, tmp_path):
    """Test workflow initialization with file:// query."""
    config = simple_config["campaign"]["ml-null-tests.mission-tests"].copy()

    # Create a query file
    query_file = tmp_path / "test_query.txt"
    query_file.write_text("obs_id IN ('1551468569.1551475843.ar5_1')\n")

    config["query"] = f"file://{query_file}"

    workflow = NullTestWorkflow(**config)

    assert workflow.query == f"file://{query_file}"
    assert workflow.datasize == 259584


def test_null_test_workflow_file_url_handling(mock_context_act, simple_config, tmp_path):
    """Test that file:// URLs are properly converted to absolute paths in arguments."""
    config = simple_config["campaign"]["ml-null-tests.mission-tests"].copy()

    # Create a test file
    test_file = tmp_path / "test_file.fits"
    test_file.write_text("test")

    config["area"] = f"file://{test_file}"

    workflow = NullTestWorkflow(**config)
    arguments = workflow.get_arguments()

    # The area argument should be converted to absolute path
    assert str(test_file.absolute()) in arguments[1]
