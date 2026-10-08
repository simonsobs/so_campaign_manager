import shlex

from socm.utils.misc import read_par_file
from socm.workflows.lat_simulation import LATSimWorkflow


def test_par_file_values_become_fields(tmp_path):
    """Translated option names from a par file map back onto workflow fields."""
    par = tmp_path / "sim.par"
    par.write_text(
        "--sample_rate=200\n"
        "--sim_noise.enable\n"
        "--sim_hwpss.atmo_data=/data/atmo.h5\n"
        "--pixels_healpix_radec.nside=1024\n"
        "--sim_atmosphere.cache_dir=/cache\n"
    )
    workflow = LATSimWorkflow(output_dir="out", **read_par_file(par))

    assert workflow.sample_rate == 200
    assert workflow.sim_noise is True
    assert workflow.sim_hwpss_atmo_data == "/data/atmo.h5"
    assert workflow.pixels_healpix_radec_nside == 1024


def test_par_file_values_round_trip_to_arguments(tmp_path):
    """Par file options, including unknown ones, are passed to the command line."""
    par = tmp_path / "sim.par"
    par.write_text(
        "--sim_noise.enable\n"
        "--sim_hwpss.atmo_data=/data/atmo.h5\n"
        "--sim_atmosphere.cache_dir=/cache\n"
    )
    arguments = LATSimWorkflow(output_dir="out", **read_par_file(par)).get_arguments()

    assert "--sim_noise.enable" in arguments
    assert "--sim_hwpss.atmo_data=/data/atmo.h5" in arguments
    assert "--sim_atmosphere.cache_dir=/cache" in arguments


def test_get_arguments_is_list_without_unset_or_internal_fields():
    workflow = LATSimWorkflow(
        output_dir="out dir",
        subcommand="",
        base_path="/base",
        resources={"ranks": 4, "threads": 2},
    )
    arguments = workflow.get_arguments()

    assert isinstance(arguments, list)
    assert arguments[:3] == ["--out", "out dir", "--job_group_size=4"]
    assert not any(arg.endswith("=None") for arg in arguments)
    for field in ("base_path", "context", "subcommand"):
        assert not any(arg.startswith(f"--{field}") for arg in arguments)


def test_get_command_quotes_for_the_shell():
    workflow = LATSimWorkflow(output_dir="out dir", resources={"ranks": 4, "threads": 2})
    tokens = shlex.split(workflow.get_command())

    assert tokens[:6] == [
        "srun", "--cpu_bind=cores", "--export=ALL", "--ntasks-per-node=4", "--cpus-per-task=2", "toast_so_sim",
    ]
    assert tokens[6:8] == ["--out", "out dir"]
