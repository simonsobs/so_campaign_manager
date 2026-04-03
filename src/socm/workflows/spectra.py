from pathlib import Path
from typing import List, Optional, Union

from socm.core import Workflow


class SpectraWorkflow(Workflow):
    """
    A workflow for ML mapmaking.
    """

    name: str = "pspipe_workflow"
    executable: str = "python -u"
    datasize: int = 0
    script_args: Optional[List[str]] = None
    script_flags: Optional[List[str]] = None

    def get_command(self) -> str:
        """
        Get the full shell command to run the ML mapmaking workflow.

        Returns
        -------
        str
            The complete srun command string with arguments.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={self.resources.ranks} --cpus-per-task={self.resources.threads} {self.executable} {self.subcommand} "
        command += " ".join(self.get_arguments())

        return command.strip()

    def get_arguments(self) -> List[str]:
        """
        Get the list of command-line arguments for the ML mapmaking workflow.

        Returns
        -------
        list of str
            The positional and keyword arguments for the workflow command.
        """

        arguments = []
        for script_arg in self.script_args if self.script_args else []:
            if script_arg.startswith("file://"):
                script_arg = Path(script_arg.split("file://")[-1]).absolute()
                script_arg = f"{script_arg.absolute()}"
                arguments.append(script_arg)
        if self.script_flags:
            for flag in self.script_flags:
                arguments.append(f"--{flag}")

        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if k not in [
                "area",
                "name",
                "output_dir",
                "base_path",
                "id",
                "environment",
                "resources",
                "datasize",
                "executable",
                "script_args",
                "script_flags",
                "depends",
                "subcommand"
            ]:
                arguments.append(f"--{k}={v}")
        return arguments

    @classmethod
    def get_workflows(
        cls, descriptions: Union[List[dict], dict]
    ) -> List["SpectraWorkflow"]:
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
