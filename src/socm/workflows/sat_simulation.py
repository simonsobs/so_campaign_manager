from pathlib import Path
from typing import Dict, Optional

from pydantic import PrivateAttr

from ..core.models import Workflow


class SATSimWorkflow(Workflow):
    """
    A workflow for ML mapmaking.
    """

    output_dir: str
    name: str = "sat_msss"
    executable: str = "toast_so_sim"
    schedule: Optional[str] = None
    bands: Optional[str] = "SAT_f090"
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

    _arg_translation: Dict[str, str] = PrivateAttr(
        {
            "sim_hwpss_atmo_data": "sim_hwpss.atmo_data",
            "pixels_healpix_radec_nside": "pixels_healpix_radec.nside",
            "filterbin_name": "filterbin.name",
            "processing_mask_file": "processing_mask.file",
        }
    )

    def get_command(self) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={self.resources['ranks']} --cpus-per-task={self.resources['threads']} {self.executable} {self.subcommand} --job_group_size={self.resources['ranks']} "
        command += self.get_arguments()

        return command.strip()

    def get_arguments(self) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        arguments = f"--out {self.output_dir} "
        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
            if k not in [
                "anme",
                "output_dir",
                "executable",
                "id",
                "environment",
                "resources",
            ]:
                if isinstance(v, bool):
                    if v:
                        arguments += f"--{k}.enable "
                    else:
                        arguments += f"--{k}.disable "
                else:
                    arguments += f"--{self._arg_translation.get(k, k)}={v} "
        return arguments.strip()
