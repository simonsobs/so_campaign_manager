import shlex

import pytest

from socm.utils.misc import read_par_file
from socm.workflows.get_schedule import GetScheduleWorkflow

# One argument per line, as toast_ground_schedule expects in an @file.
PAR_CONTENT = """\
--block-out
01/15-03/15
--equalize-time
--out
schedules/schedule_lat.txt
--site-lat
-22.958064
--site-name
ATACAMA
--start
2025-01-01 00:00:00
--stop
2026-01-01 00:00:00
--patch
RISING_SCAN_40,HORIZONTAL,1.00,30.00,150.00,40.00,1440
--patch
SETTING_SCAN_40,HORIZONTAL,1.00,210.00,330.00,40.00,1440
"""


@pytest.fixture
def par_file(tmp_path):
    path = tmp_path / "schedule_param.par"
    path.write_text(PAR_CONTENT)
    return path


@pytest.fixture
def make_workflow(par_file):
    def _make(**overrides):
        config = {**read_par_file(par_file), "output_dir": "/base", "resources": {"ranks": 1, "threads": 1}}
        config.update(overrides)
        return GetScheduleWorkflow(**config)

    return _make


def test_par_maps_start_stop_out(make_workflow):
    workflow = make_workflow()
    assert workflow.start.isoformat(sep=" ") == "2025-01-01 00:00:00"
    assert workflow.stop.isoformat(sep=" ") == "2026-01-01 00:00:00"
    assert workflow.output_dir == "schedules/schedule_lat.txt"


def test_par_command_round_trips(make_workflow):
    tokens = shlex.split(make_workflow().get_command())

    # start/stop/out are emitted exactly once
    assert sum(t.startswith("--start") for t in tokens) == 1
    assert sum(t.startswith("--stop") for t in tokens) == 1
    assert tokens.count("--out") == 1
    assert tokens[tokens.index("--out") + 1] == "schedules/schedule_lat.txt"

    # flags stand alone, repeated options are repeated, negative values survive
    assert "--equalize-time" in tokens
    assert sum(t.startswith("--patch=") for t in tokens) == 2
    assert "--patch=RISING_SCAN_40,HORIZONTAL,1.00,30.00,150.00,40.00,1440" in tokens
    assert "--site-lat=-22.958064" in tokens
    assert "--block-out=01/15-03/15" in tokens


def test_value_with_spaces_is_quoted(make_workflow):
    tokens = shlex.split(make_workflow(**{"site-name": "Cerro Toco"}).get_command())
    assert "--site-name=Cerro Toco" in tokens


def test_get_arguments_is_unquoted_list(make_workflow):
    """Enactors pass arguments to the executable as-is: one entry each, no shell quoting."""
    arguments = make_workflow().get_arguments()
    assert isinstance(arguments, list)
    assert arguments[:2] == ["--out", "schedules/schedule_lat.txt"]
    assert "--start=2025-01-01 00:00:00" in arguments
    assert "--stop=2026-01-01 00:00:00" in arguments
    assert not any("'" in arg for arg in arguments)
