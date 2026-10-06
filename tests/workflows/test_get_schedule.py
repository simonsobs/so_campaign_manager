import shlex
from datetime import datetime
from pathlib import Path

from socm.utils.misc import read_par_file
from socm.workflows.get_schedule import GetScheduleWorkflow

EXAMPLE_PAR = Path(__file__).parents[2] / "examples" / "schedule_param.par"


def _workflow(**overrides):
    config = {**read_par_file(EXAMPLE_PAR), "output_dir": "/base", "resources": {"ranks": 1, "threads": 1}}
    config.update(overrides)
    return GetScheduleWorkflow(**config)


def test_example_par_maps_start_stop_out():
    workflow = _workflow()
    assert workflow.start == datetime(2025, 1, 1)
    assert workflow.stop == datetime(2026, 1, 1)
    assert workflow.output_dir == "schedules/schedule_lat.txt"


def test_example_par_command_round_trips():
    tokens = shlex.split(_workflow().get_command())

    # start/stop/out are emitted exactly once
    assert sum(t.startswith("--start") for t in tokens) == 1
    assert sum(t.startswith("--stop") for t in tokens) == 1
    assert tokens.count("--out") == 1
    assert tokens[tokens.index("--out") + 1] == "schedules/schedule_lat.txt"

    # flags stand alone, repeated options are repeated, negative values survive
    assert "--equalize-time" in tokens
    assert sum(t.startswith("--patch=") for t in tokens) == 6
    assert "--patch=RISING_SCAN_40,HORIZONTAL,1.00,30.00,150.00,40.00,1440" in tokens
    assert "--site-lat=-22.958064" in tokens
    assert "--block-out=01/15-03/15" in tokens


def test_value_with_spaces_is_quoted():
    tokens = shlex.split(_workflow(**{"site-name": "Cerro Toco"}).get_command())
    assert "--site-name=Cerro Toco" in tokens


def test_get_arguments_is_unquoted_list():
    """Enactors pass arguments to the executable as-is: one entry each, no shell quoting."""
    arguments = _workflow().get_arguments()
    assert isinstance(arguments, list)
    assert arguments[:2] == ["--out", "schedules/schedule_lat.txt"]
    assert "--start=2025-01-01 00:00:00" in arguments
    assert "--stop=2026-01-01 00:00:00" in arguments
    assert not any("'" in arg for arg in arguments)
