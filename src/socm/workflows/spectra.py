from pathlib import Path
from typing import List, Optional, Union

from socm.core import Workflow


class SpectraWorkflow(Workflow):
    """
    Workflow for power-spectrum estimation using PSpipe.

    Executes an arbitrary PSpipe Python script via ``python -u <subcommand>``.
    Positional script arguments (``script_args``) are passed before any
    keyword flags. ``file://`` URIs in ``script_args`` are resolved to absolute
    paths at argument-building time.

    Parameters
    ----------
    name : str, optional
        Human-readable workflow name. Defaults to ``"pspipe_workflow"``.
    executable : str, optional
        Executable to invoke. Defaults to ``"python -u"``.
    datasize : int, optional
        Estimated data volume (reserved for future use by the planner).
        Defaults to ``0``.
    script_args : list of str or None, optional
        Positional arguments to pass to the script. ``file://`` URIs are
        resolved to absolute paths. Defaults to ``None``.
    script_flags : list of str or None, optional
        Boolean flags appended as ``--flag`` (without values). Defaults to
        ``None``.
    """

    name: str = "pspipe_workflow"
    executable: str = "python -u"
    datasize: int = 0
    script_args: Optional[List[str]] = None
    script_flags: Optional[List[str]] = None

    def get_command(self) -> str:
        """
        Build the full ``srun`` command string for the power-spectra workflow.

        Constructs an ``srun`` invocation using the resource specification
        (``ranks``, ``threads``) and appends all arguments from
        :meth:`get_arguments`.

        Returns
        -------
        str
            The complete shell command string, stripped of trailing whitespace.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={self.resources.ranks} --cpus-per-task={self.resources.threads} {self.executable} {self.subcommand} "
        command += " ".join(self.get_arguments())

        return command.strip()

    def get_arguments(self) -> List[str]:
        """
        Build the list of command-line arguments for the power-spectra workflow.

        Resolves ``file://`` URIs in ``script_args`` to absolute paths, appends
        each item in ``script_flags`` as ``--flag``, and then appends
        ``--key=value`` options for every set field not in the exclusion list
        (``area``, ``name``, ``output_dir``, ``base_path``, ``id``,
        ``environment``, ``resources``, ``datasize``, ``executable``,
        ``script_args``, ``script_flags``, ``depends``, ``subcommand``).

        Returns
        -------
        list of str
            Ordered list of argument strings.
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
        Create :class:`SpectraWorkflow` instances from configuration descriptions.

        Parameters
        ----------
        descriptions : dict or list of dict
            A single workflow configuration dictionary or a list of them.
            Each dictionary is passed as keyword arguments to the constructor.

        Returns
        -------
        list of SpectraWorkflow
            One instantiated workflow per configuration dictionary.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]

        workflows = []
        for desc in descriptions:
            workflow = cls(**desc)
            workflows.append(workflow)

        return workflows
