import shlex
import subprocess
from pathlib import Path

import pytest

from socm.workflows import registered_workflows
from socm.workflows.shell_script import ShellScriptWorkflow

SPLIT_SCRIPT = Path(__file__).parents[2] / "examples" / "scripts" / "split_schedule_months.sh"


def test_registered():
    assert registered_workflows["shell-script"] is ShellScriptWorkflow


def test_get_arguments_is_script_then_args():
    workflow = ShellScriptWorkflow(script="/scripts/run.sh", script_args=["a b", "2"])
    assert workflow.executable == "bash"
    assert workflow.get_arguments() == ["/scripts/run.sh", "a b", "2"]


def test_script_args_yaml_alias_and_file_uri(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workflow = ShellScriptWorkflow(**{"script": "file://run.sh", "script-args": ["file://in.txt", "plain"]})
    assert workflow.get_arguments() == [str(tmp_path / "run.sh"), str(tmp_path / "in.txt"), "plain"]


def test_get_command_quotes_for_the_shell():
    workflow = ShellScriptWorkflow(
        script="/my scripts/run.sh", script_args=["a b"], resources={"ranks": 1, "threads": 3}
    )
    assert shlex.split(workflow.get_command()) == [
        "srun", "--ntasks=1", "--cpus-per-task=3", "bash", "/my scripts/run.sh", "a b",
    ]


def _schedule_row(date: str, leading_space: bool) -> str:
    row = f"{date} 00:00:00  {date} 01:00:00     0.00 RISING_SCAN_40   30.00  150.00  40.00  0  0"
    return (" " + row) if leading_space else row


@pytest.mark.parametrize("leading_space", [True, False])
def test_split_schedule_months_script(tmp_path, leading_space):
    """Split k gets days 1..NDAYS of months k, k+NSPLIT, ...; header is copied to every split."""
    header = ["#Site Telescope", "ATACAMA LAT", "#Start time UTC ..."]
    dates = ["2025-01-01", "2025-01-03", "2025-01-04", "2025-02-02", "2025-03-01", "2025-05-02", "2025-12-15"]
    full = tmp_path / "full.txt"
    full.write_text("\n".join(header + [_schedule_row(d, leading_space) for d in dates]) + "\n")
    out_dir = tmp_path / "split"

    subprocess.run(["bash", str(SPLIT_SCRIPT), str(full), str(out_dir), "4", "3"], check=True)

    def split_dates(k):
        lines = (out_dir / f"schedule.{k}.txt").read_text().splitlines()
        assert lines[:3] == header
        return [line.split()[0] for line in lines[3:]]

    # day 4 is beyond NDAYS=3, day 15 too; month 5 belongs to split 1 (5 = 1 + 4)
    assert split_dates(1) == ["2025-01-01", "2025-01-03", "2025-05-02"]
    assert split_dates(2) == ["2025-02-02"]
    assert split_dates(3) == ["2025-03-01"]
    assert split_dates(4) == []


def test_split_schedule_months_script_usage_error(tmp_path):
    result = subprocess.run(["bash", str(SPLIT_SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "Usage" in result.stderr
