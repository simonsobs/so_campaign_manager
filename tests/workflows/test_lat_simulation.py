import shlex

import pytest

from socm.utils.misc import read_par_file
from socm.workflows.lat_simulation import LATSimWorkflow

QUANTITY = 'Quantity("0.0004304 K s(1/2)")'


def test_minimal_workflow_has_only_required_arguments():
    """Unset options and internal fields never reach the command line."""
    workflow = LATSimWorkflow(output_dir="out", base_path="/base", resources={"ranks": 34, "threads": 56})

    assert workflow.get_arguments() == ["--out", "out", "--job_group_size=1"]


def test_job_group_size_does_not_follow_ranks():
    """pwg runs with groupsize=1 regardless of the rank count."""
    resources = {"ranks": 272, "threads": 7}

    assert "--job_group_size=1" in LATSimWorkflow(output_dir="o", resources=resources).get_arguments()
    assert "--job_group_size=4" in LATSimWorkflow(
        output_dir="o", job_group_size=4, resources=resources
    ).get_arguments()


def test_plain_flags_and_operator_toggles():
    """sort_schedule is a bare flag; every other boolean is --op.enable / --op.disable."""
    arguments = LATSimWorkflow(output_dir="o", sort_schedule=True, sim_noise=True, sim_sss=False).get_arguments()

    assert "--sort_schedule" in arguments
    assert "--sim_noise.enable" in arguments
    assert "--sim_sss.disable" in arguments
    assert not any(arg.startswith("--sort_schedule.") for arg in arguments)


def test_disabled_plain_flag_is_omitted():
    arguments = LATSimWorkflow(output_dir="o", sort_schedule=False).get_arguments()

    assert not any("sort_schedule" in arg for arg in arguments)


def test_operators_mapping_is_flattened():
    workflow = LATSimWorkflow(
        output_dir="o",
        operators={
            "sim_sss": False,
            "scan_alm": {"enable": True, "file": "/maps/cmb_{wafer_slot}.fits"},
            "mlmapmaker": {"nmat_mode": "load"},
        },
    )
    arguments = workflow.get_arguments()

    assert "--sim_sss.disable" in arguments
    assert "--scan_alm.enable" in arguments
    assert "--scan_alm.file=/maps/cmb_{wafer_slot}.fits" in arguments  # toast's own placeholder kept
    assert "--mlmapmaker.nmat_mode=load" in arguments
    # An operator that only sets traits is not toggled; the toast config decides.
    assert not any(arg.startswith(("--mlmapmaker.enable", "--mlmapmaker.disable")) for arg in arguments)
    assert not any(arg.startswith("--operators") for arg in arguments)


def test_flat_keys_override_operators():
    workflow = LATSimWorkflow(
        output_dir="o",
        operators={"mlmapmaker": {"nmat_mode": "cache"}},
        **{"mlmapmaker.nmat_mode": "load"},
    )
    arguments = workflow.get_arguments()

    assert "--mlmapmaker.nmat_mode=load" in arguments
    assert "--mlmapmaker.nmat_mode=cache" not in arguments


def test_par_file_flat_keys_and_operators_are_equivalent(tmp_path):
    """The three ways of giving toast options produce the same command line."""
    par = tmp_path / "signal.par"
    par.write_text(
        "# signal run\n"
        "--sim_noise.disable\n"
        "--scan_alm.enable\n"
        "--scan_alm.file=/maps/x.fits\n"
        "--sort_schedule\n"
        "--sample_rate=100\n"
    )
    from_par = LATSimWorkflow(output_dir="o", **read_par_file(par))
    from_flat = LATSimWorkflow(
        output_dir="o",
        sort_schedule=True,
        sample_rate=100,
        **{"sim_noise": False, "scan_alm": True, "scan_alm.file": "/maps/x.fits"},
    )
    from_operators = LATSimWorkflow(
        output_dir="o",
        sort_schedule=True,
        sample_rate=100,
        operators={"sim_noise": False, "scan_alm": {"enable": True, "file": "/maps/x.fits"}},
    )

    assert from_par.get_arguments() == from_flat.get_arguments() == from_operators.get_arguments()


def test_repeated_option_becomes_one_argument_per_value(tmp_path):
    """A list (e.g. an option repeated in a par file) is passed once per item, in order."""
    par = tmp_path / "sim.par"
    par.write_text("--scan_alm.focalplane_keys=wafer_slot\n--scan_alm.focalplane_keys=band\n")
    arguments = LATSimWorkflow(output_dir="o", **read_par_file(par)).get_arguments()

    keys = [arg for arg in arguments if arg.startswith("--scan_alm.focalplane_keys=")]
    assert keys == ["--scan_alm.focalplane_keys=wafer_slot", "--scan_alm.focalplane_keys=band"]


def test_out_option_becomes_output_dir_and_is_not_duplicated(tmp_path):
    par = tmp_path / "sim.par"
    par.write_text("--out=/scratch/noise\n--sim_noise.enable\n")
    workflow = LATSimWorkflow(**read_par_file(par))
    arguments = workflow.get_arguments()

    assert workflow.output_dir == "/scratch/noise"
    assert arguments[:2] == ["--out", "/scratch/noise"]
    assert arguments.count("--out") == 1
    assert not any(arg.startswith("--out=") for arg in arguments)


def test_file_urls_become_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workflow = LATSimWorkflow(
        output_dir="o",
        config="file://cfg/mss-0003_lat.yaml",
        **{"mlmapmaker.area": ["file://geo/a.fits", "/abs/b.fits"]},
    )
    arguments = workflow.get_arguments()

    assert f"--config={tmp_path / 'cfg' / 'mss-0003_lat.yaml'}" in arguments
    assert f"--mlmapmaker.area={tmp_path / 'geo' / 'a.fits'}" in arguments
    assert "--mlmapmaker.area=/abs/b.fits" in arguments


def test_values_with_spaces_and_quotes_pass_unchanged():
    """No pwg-style '...' shell quoting is needed: the arguments are a list."""
    workflow = LATSimWorkflow(
        output_dir="out dir",
        resources={"ranks": 2, "threads": 4},
        **{"common_mode_noise": True, "common_mode_noise.NET": QUANTITY},
    )

    assert f"--common_mode_noise.NET={QUANTITY}" in workflow.get_arguments()
    assert f"--common_mode_noise.NET={QUANTITY}" in shlex.split(workflow.get_command())


def test_get_command_uses_total_ranks():
    workflow = LATSimWorkflow(
        output_dir="out dir",
        executable="/envs/lat/bin/toast_so_sim",
        resources={"ranks": 272, "threads": 7},
    )
    tokens = shlex.split(workflow.get_command())

    assert tokens[:7] == [
        "srun", "--export=ALL", "--ntasks=272", "--cpus-per-task=7",
        "--distribution=block:block", "--cpu-bind=none", "/envs/lat/bin/toast_so_sim",
    ]
    assert tokens[7:9] == ["--out", "out dir"]


def test_included_par_file_overrides_scalar_field(tmp_path):
    """A repeated option that targets a scalar field keeps its last value, as argparse does."""
    (tmp_path / "base.par").write_text("--sample_rate=37\n--bands=LAT_f090\n")
    (tmp_path / "sim.par").write_text("@base.par\n--sample_rate=100\n")
    workflow = LATSimWorkflow(output_dir="o", **read_par_file(tmp_path / "sim.par"))
    arguments = workflow.get_arguments()

    assert workflow.sample_rate == 100
    assert "--sample_rate=100" in arguments
    assert "--sample_rate=37" not in arguments


def test_list_fields_keep_every_value():
    workflow = LATSimWorkflow(output_dir="o", depends=["get-schedule", "split-schedule"])

    assert workflow.depends == ["get-schedule", "split-schedule"]


def test_normalize_options_is_idempotent():
    options = {"out": "/o", "operators": {"scan_alm": {"enable": True, "file": "/m.fits"}}, "sim_noise": False}
    once = LATSimWorkflow.normalize_options(options)

    assert once == {"output_dir": "/o", "scan_alm": True, "scan_alm.file": "/m.fits", "sim_noise": False}
    assert LATSimWorkflow.normalize_options(once) == once
    assert "operators" in options  # the input is not modified


def test_boolean_traits_use_toast_trait_flags():
    """A boolean trait is --op.trait / --op.no_trait, never .enable/.disable or =False."""
    arguments = LATSimWorkflow(
        output_dir="o",
        operators={"mlmapmaker": {"enable": True, "deslope": False, "write_bin": True}},
    ).get_arguments()

    assert "--mlmapmaker.enable" in arguments
    assert "--mlmapmaker.no_deslope" in arguments
    assert "--mlmapmaker.write_bin" in arguments
    assert not any(arg.startswith(("--mlmapmaker.deslope", "--mlmapmaker.write_bin.")) for arg in arguments)


def test_no_trait_flag_from_par_file_round_trips(tmp_path):
    par = tmp_path / "sim.par"
    par.write_text("--mapmaker.no_write_map\n--mapmaker.write_invcov\n")
    workflow = LATSimWorkflow(output_dir="o", **read_par_file(par))
    arguments = workflow.get_arguments()

    assert "--mapmaker.no_write_map" in arguments
    assert "--mapmaker.write_invcov" in arguments
    assert not any(arg.endswith((".enable", ".disable")) for arg in arguments)


def test_stage_boolean_trait_overrides_par_no_flag():
    """--op.no_trait in the par file and op.trait: true in the stage are the same option."""
    par = LATSimWorkflow.normalize_options({"mapmaker.no_write_map": True})
    stage = LATSimWorkflow.normalize_options({"operators": {"mapmaker": {"write_map": True}}})
    arguments = LATSimWorkflow(output_dir="o", **{**par, **stage}).get_arguments()

    assert "--mapmaker.write_map" in arguments
    assert "--mapmaker.no_write_map" not in arguments


def test_last_trait_flag_in_par_file_wins(tmp_path):
    par = tmp_path / "sim.par"
    par.write_text("--mapmaker.write_map\n--mapmaker.no_write_map\n")
    arguments = LATSimWorkflow(output_dir="o", **read_par_file(par)).get_arguments()

    assert "--mapmaker.no_write_map" in arguments
    assert "--mapmaker.write_map" not in arguments


def test_flat_negative_trait_overrides_operators():
    """Flat keys win over operators in either form of a boolean trait."""
    negative = LATSimWorkflow(
        output_dir="o",
        operators={"mapmaker": {"write_map": True}},
        **{"mapmaker.no_write_map": True},
    ).get_arguments()
    positive = LATSimWorkflow(
        output_dir="o",
        operators={"mapmaker": {"no_write_map": True}},
        **{"mapmaker.write_map": True},
    ).get_arguments()

    assert "--mapmaker.no_write_map" in negative
    assert "--mapmaker.write_map" not in negative
    assert "--mapmaker.write_map" in positive
    assert "--mapmaker.no_write_map" not in positive


def test_both_forms_of_a_trait_in_one_source_must_agree():
    with pytest.raises(ValueError, match="'mapmaker.write_map' and 'mapmaker.no_write_map' are both set"):
        LATSimWorkflow(output_dir="o", **{"mapmaker.write_map": True, "mapmaker.no_write_map": True})

    agreeing = LATSimWorkflow(output_dir="o", **{"mapmaker.write_map": False, "mapmaker.no_write_map": True})
    assert "--mapmaker.no_write_map" in agreeing.get_arguments()
