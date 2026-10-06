import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import PrivateAttr, model_validator

from ..core.models import Workflow

# Workflow field name -> toast_so_sim option name.
_ARG_TRANSLATION = {
    "sim_hwpss_atmo_data": "sim_hwpss.atmo_data",
    "pixels_healpix_radec_nside": "pixels_healpix_radec.nside",
    "filterbin_name": "filterbin.name",
    "processing_mask_file": "processing_mask.file",
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
}


class LATSimWorkflow(Workflow):
    """
    A workflow for simulating SAT observations.
    """

    output_dir: str
    name: str = "lat_sims"
    executable: str = "toast_so_sim"
    schedule: Optional[str] = None
    bands: Optional[str] = "LAT_f090"
    wafer_slots: Optional[str] = "w25"
    sample_rate: int = 37
    sim_noise: bool = False
    scan_map: bool = False
    sim_atmosphere: bool = False
    sim_sss: bool = False
    sim_hwpss: bool = False
    sim_hwpss_atmo_data: Optional[str] = None
    pixels_healpix_radec_nside: int = 512
    filterbin_name: Optional[str] = None
    processing_mask_file: Optional[str] = None

    _arg_translation: Dict[str, str] = PrivateAttr(_ARG_TRANSLATION)

    @model_validator(mode="before")
    @classmethod
    def _untranslate_option_names(cls, data: Any) -> Any:
        """Map command-line option names (e.g. from a par file) to field names."""
        if isinstance(data, dict):
            reverse = {option: field for field, option in _ARG_TRANSLATION.items()}
            data = {reverse.get(k, k): v for k, v in data.items()}
        return data

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
            "--cpu_bind=cores",
            "--export=ALL",
            f"--ntasks-per-node={self.resources.ranks}",
            f"--cpus-per-task={self.resources.threads}",
            self.executable,
        ]
        if self.subcommand:
            srun.append(self.subcommand)
        return shlex.join(srun + self.get_arguments())

    def get_arguments(self, **kargs: Any) -> List[str]:
        """
        Get the command-line arguments for the LAT simulation workflow.

        Returns
        -------
        list of str
            One entry per argument, without shell quoting.
        """
        arguments = ["--out", self.output_dir, f"--job_group_size={self.resources.ranks}"]

        for k, v in sorted(self.model_dump().items()):
            if k in _NOT_ARGUMENTS or v is None:
                continue
            option = self._arg_translation.get(k, k)
            if isinstance(v, bool):
                arguments.append(f"--{option}.enable" if v else f"--{option}.disable")
                continue
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
            arguments.append(f"--{option}={v}")
        return arguments
