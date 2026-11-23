import shlex
from pathlib import Path
from typing import Any

from pydantic import model_validator

from ..core.models import Workflow

# toast_so_sim option name -> workflow field name.
_OPTION_TO_FIELD = {
    "out": "output_dir",
}

# toast_so_sim options that are plain flags. Every other boolean is an
# operator toggle and becomes --<op>.enable / --<op>.disable.
_FLAGS = {
    "sort_schedule",
}

# Workflow fields that are not toast_so_sim options.
_NOT_ARGUMENTS = {
    "name",
    "output_dir",
    "executable",
    "id",
    "environment",
    "resources",
    "depends",
    "base_path",
    "context",
    "subcommand",
    "job_group_size",
}


def _flatten_operators(operators: dict[str, Any]) -> dict[str, Any]:
    """
    Turn an ``operators`` mapping into toast_so_sim option names, the same
    representation ``read_par_file`` returns.

    ``{"sim_noise": True}`` stays ``{"sim_noise": True}``, and
    ``{"mlmapmaker": {"enable": True, "nmat_mode": "load"}}`` becomes
    ``{"mlmapmaker": True, "mlmapmaker.nmat_mode": "load"}``.
    """
    options: dict[str, Any] = {}
    for op, value in operators.items():
        if not isinstance(value, dict):
            options[op] = value
            continue
        for trait, trait_value in value.items():
            if trait == "enable":
                options[op] = trait_value
            else:
                options[f"{op}.{trait}"] = trait_value
    return options


class LATSimWorkflow(Workflow):
    """
    A workflow for simulating LAT observations with ``toast_so_sim``.

    Only the options every LAT run sets are fields. Any other toast option is
    passed through under its command-line name: ``op: bool`` for
    ``--op.enable``/``--op.disable`` and ``"op.trait": value`` for
    ``--op.trait=value``. Those options can come from a par file, from flat
    keys in the stage config, or from an ``operators`` mapping.
    """

    output_dir: str
    name: str = "lat_sims"
    executable: str = "toast_so_sim"
    config: str | None = None
    schedule: str | None = None
    sort_schedule: bool = False
    bands: str | None = None
    tube_slots: str | None = None
    sample_rate: int | None = None
    job_group_size: int = 1

    @classmethod
    def normalize_options(cls, options: dict[str, Any]) -> dict[str, Any]:
        """
        Map toast_so_sim option names to fields (``--out`` -> ``output_dir``)
        and flatten an ``operators`` mapping into option names. Within one
        source, flat keys given next to ``operators`` take precedence.
        """
        options = dict(options)
        for option, field in _OPTION_TO_FIELD.items():
            if option in options:
                options[field] = options.pop(option)
        for key, value in _flatten_operators(options.pop("operators", None) or {}).items():
            options.setdefault(key, value)
        return options

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        return cls.normalize_options(data) if isinstance(data, dict) else data

    def get_command(self, **kargs: Any) -> str:
        """
        Get the full shell command to run the LAT simulation workflow.

        Returns
        -------
        str
            The complete srun command string with arguments.
        """
        if self.resources is None:
            raise ValueError("Resources must be set before calling get_command")
        srun = [
            "srun",
            "--export=ALL",
            f"--ntasks={self.resources.ranks}",
            f"--cpus-per-task={self.resources.threads}",
            "--distribution=block:block",
            "--cpu-bind=none",
            self.executable,
        ]
        if self.subcommand:
            srun.append(self.subcommand)
        return shlex.join(srun + self.get_arguments())

    def get_arguments(self, **kargs: Any) -> list[str]:
        """
        Get the command-line arguments for the LAT simulation workflow.

        Returns
        -------
        list of str
            One entry per argument, without shell quoting.
        """
        arguments = ["--out", self.output_dir, f"--job_group_size={self.job_group_size}"]

        for k, v in sorted(self.model_dump().items()):
            if k in _NOT_ARGUMENTS or v is None:
                continue
            if isinstance(v, bool):
                if k in _FLAGS:
                    if v:
                        arguments.append(f"--{k}")
                else:
                    arguments.append(f"--{k}.enable" if v else f"--{k}.disable")
                continue
            # Repeated options are stored as lists.
            for item in v if isinstance(v, list) else [v]:
                if isinstance(item, str) and item.startswith("file://"):
                    item = Path(item.removeprefix("file://")).absolute()
                arguments.append(f"--{k}={item}")
        return arguments

    @classmethod
    def get_workflows(cls, descriptions: list[dict] | dict) -> list["LATSimWorkflow"]:
        """
        Create LATSimWorkflow instances from configuration descriptions.

        Parameters
        ----------
        descriptions : dict or list of dict
            One or more workflow configuration dictionaries.

        Returns
        -------
        list of LATSimWorkflow
            The instantiated workflow objects.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]
        return [cls(**desc) for desc in descriptions]
