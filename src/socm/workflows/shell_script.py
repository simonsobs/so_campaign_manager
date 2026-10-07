import shlex
from pathlib import Path
from typing import Any, List, Union

from pydantic import ConfigDict, Field

from ..core.models import Workflow


def _resolve_file_uri(value: str) -> str:
    """Turn a ``file://`` value into an absolute path; leave anything else as is."""
    if value.startswith("file://"):
        return str(Path(value.split("file://")[-1]).absolute())
    return value


class ShellScriptWorkflow(Workflow):
    """
    A workflow that runs a user-provided shell script with ``bash``.

    Used for small processing steps between other workflows (e.g. splitting a
    schedule) without requiring socm on the compute node.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = "shell_script"
    executable: str = "bash"
    script: str
    script_args: List[str] = Field(default_factory=list, alias="script-args")

    def get_command(self, **kargs: Any) -> str:
        """
        Get the full shell command to run the script.

        Returns
        -------
        str
            The complete srun command string with arguments.
        """
        srun = [
            "srun",
            "--ntasks=1",
            f"--cpus-per-task={self.resources.threads}",
            self.executable,
        ]
        return shlex.join(srun + self.get_arguments())

    def get_arguments(self, **kargs: Any) -> List[str]:
        """
        Get the script path followed by its positional arguments.

        Returns
        -------
        list of str
            One entry per argument, without shell quoting.
        """
        return [_resolve_file_uri(self.script)] + [_resolve_file_uri(str(arg)) for arg in self.script_args]

    @classmethod
    def get_workflows(cls, descriptions: Union[List[dict], dict]) -> List["ShellScriptWorkflow"]:
        """
        Create ShellScriptWorkflow instances from configuration descriptions.

        Parameters
        ----------
        descriptions : dict or list of dict
            One or more workflow configuration dictionaries.

        Returns
        -------
        list of ShellScriptWorkflow
            The instantiated workflow objects.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]

        return [cls(**desc) for desc in descriptions]
