import shlex

from socm.workflows import SATSimWorkflow


def test_get_arguments_is_unquoted_list():
    """Enactors pass arguments to the executable as-is: one entry each, no shell quoting."""
    workflow = SATSimWorkflow(output_dir="out dir", resources={"ranks": 2, "threads": 1})
    arguments = workflow.get_arguments()

    assert isinstance(arguments, list)
    assert arguments[:3] == ["--out", "out dir", "--job_group_size=2"]
    assert not any(arg.endswith(("=None", " ")) for arg in arguments)


def test_get_arguments_skips_internal_fields():
    workflow = SATSimWorkflow(
        output_dir="out",
        context="context.yaml",
        subcommand="",
        base_path="/base",
        resources={"ranks": 1, "threads": 1},
    )
    arguments = workflow.get_arguments()

    for field in ("context", "subcommand", "base_path"):
        assert not any(arg.startswith(f"--{field}") for arg in arguments)


def test_get_arguments_translates_option_names():
    workflow = SATSimWorkflow(
        output_dir="out",
        sim_hwpss=True,
        sim_hwpss_atmo_data="/data/atmo.h5",
        resources={"ranks": 1, "threads": 1},
    )
    arguments = workflow.get_arguments()

    assert "--sim_hwpss.enable" in arguments
    assert "--sim_hwpss.atmo_data=/data/atmo.h5" in arguments
    assert "--sim_noise.disable" in arguments


def test_get_command_quotes_for_the_shell():
    workflow = SATSimWorkflow(output_dir="out dir", resources={"ranks": 4, "threads": 2})
    tokens = shlex.split(workflow.get_command())

    assert tokens[:6] == [
        "srun", "--cpu_bind=cores", "--export=ALL", "--ntasks-per-node=4", "--cpus-per-task=2", "toast_so_sim",
    ]
    assert tokens[6:8] == ["--out", "out dir"]
