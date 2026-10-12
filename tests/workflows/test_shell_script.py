import shlex
import subprocess

from socm.workflows import registered_workflows
from socm.workflows.shell_script import ShellScriptWorkflow


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


def test_runs_script_with_arguments_intact(tmp_path):
    """Running executable + get_arguments() (as the enactors do) gives the script each argument unchanged."""
    script = tmp_path / "record args.sh"
    script.write_text('for arg in "$@"; do printf "%s\\n" "$arg"; done > "$(dirname "$0")/args.txt"\n')
    args = ["plain", "with space", "--opt=a b", "-22.9"]
    workflow = ShellScriptWorkflow(script=str(script), script_args=args)

    subprocess.run([workflow.executable, *workflow.get_arguments()], check=True)

    assert (tmp_path / "args.txt").read_text().splitlines() == args


def test_failing_script_returns_its_exit_code(tmp_path):
    script = tmp_path / "fail.sh"
    script.write_text("echo boom >&2\nexit 3\n")
    workflow = ShellScriptWorkflow(script=str(script))

    result = subprocess.run(
        [workflow.executable, *workflow.get_arguments()], capture_output=True, text=True, check=False
    )

    assert result.returncode == 3
    assert "boom" in result.stderr
