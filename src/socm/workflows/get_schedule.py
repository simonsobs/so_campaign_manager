import shlex
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import model_validator

from ..core.models import Workflow

# toast_ground_schedule option name -> workflow field name.
_OPTION_TO_FIELD = {
    "out": "output_dir",
}

# Workflow fields that are not toast_ground_schedule options.
_NOT_ARGUMENTS = {
    "name",
    "output_dir",
    "executable",
    "id",
    "environment",
    "resources",
    "script_args",
    "depends",
    "base_path",
    "context",
    "subcommand",
}


class GetScheduleWorkflow(Workflow):
    """
    A workflow for simulating SAT observations.
    """

    output_dir: str
    name: str = "sim_schedule"
    executable: str = "toast_ground_schedule"
    # Naive UTC on purpose: toast_ground_schedule expects "YYYY-MM-DD HH:MM:SS"
    # without an offset, which is what a naive datetime's isoformat gives.
    start: datetime = datetime(2000, 1, 1)  # noqa: DTZ001
    stop: datetime = datetime(2000, 1, 1)  # noqa: DTZ001
    script_args: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _untranslate_option_names(cls, data: Any) -> Any:
        """
        Map toast_ground_schedule options (e.g. from a par file) to the fields
        that ``get_command`` and ``get_arguments`` always emit, so they are not
        passed twice. An explicit ``--out`` wins over the default output_dir.
        """
        if isinstance(data, dict):
            data = dict(data)
            for option, field in _OPTION_TO_FIELD.items():
                if option in data:
                    data[field] = data.pop(option)
        return data

    def get_command(self, **kargs: Any) -> str:
        """
        Get the full shell command to run the schedule workflow.

        Returns
        -------
        str
            The complete srun command string with arguments.
        """
        if self.resources is None:
            raise ValueError("Resources must be set before calling get_command")
        srun = [
            "srun",
            "--cpu_bind=cores",
            "--export=ALL",
            "--ntasks=1",
            f"--cpus-per-task={self.resources.threads}",
            self.executable,
        ]
        return shlex.join(srun + self.get_arguments())

    def get_arguments(self, **kargs: Any) -> list[str]:
        """
        Get the command-line arguments for the schedule workflow.

        Returns
        -------
        list of str
            One entry per argument, without shell quoting.
        """
        arguments = ["--out", self.output_dir]
        for script_arg in self.script_args or []:
            if script_arg.startswith("file://"):
                script_arg = str(Path(script_arg.split("file://")[-1]).absolute())
            arguments.append(script_arg)

        for k, v in sorted(self.model_dump().items()):
            if k in _NOT_ARGUMENTS or v is None:
                continue
            if isinstance(v, bool):
                if v:
                    arguments.append(f"--{k}")
                continue
            # Repeated options (e.g. --patch) are stored as lists.
            for item in v if isinstance(v, list) else [v]:
                if isinstance(item, str) and item.startswith("file://"):
                    item = Path(item.split("file://")[-1]).absolute()
                elif isinstance(item, datetime):
                    item = item.isoformat(sep=" ")
                arguments.append(f"--{k}={item}")
        return arguments

    @classmethod
    def get_workflows(
        cls, descriptions: list[dict] | dict
    ) -> list["GetScheduleWorkflow"]:
        """
        Create SpectraWorkflow instances from configuration descriptions.

        Parameters
        ----------
        descriptions : dict or list of dict
            One or more workflow configuration dictionaries.

        Returns
        -------
        list of SpectraWorkflow
            The instantiated workflow objects.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]

        workflows = []
        for desc in descriptions:
            workflow = cls(**desc)
            workflows.append(workflow)

        return workflows
