import shlex
from pathlib import Path
from typing import Any

from pydantic import PrivateAttr

from ..core.models import Workflow

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


class SATSimWorkflow(Workflow):
    """
    Workflow for simulating Small Aperture Telescope (SAT) observations using TOAST.

    Invokes ``toast_so_sim`` to generate synthetic time-ordered data (TODs)
    with optional noise, atmosphere, and half-wave-plate synchronous signal
    (HWPSS) simulations. Parameters that map to dotted TOAST argument names
    are translated via the internal ``_arg_translation`` dictionary.

    Parameters
    ----------
    output_dir : str
        Directory where simulation outputs will be written.
    name : str, optional
        Human-readable workflow name. Defaults to ``"sat_sims"``.
    executable : str, optional
        Executable name. Defaults to ``"toast_so_sim"``.
    schedule : str or None, optional
        Path (or ``file://`` URI) to the observation schedule file.
        ``None`` means no external schedule file is used.
    bands : str or None, optional
        Frequency band identifier (e.g. ``"SAT_f090"``). Defaults to
        ``"SAT_f090"``.
    wafer_slots : str or None, optional
        Wafer slot identifier (e.g. ``"w25"``). Defaults to ``"w25"``.
    sample_rate : int, optional
        Detector sampling rate in Hz. Defaults to ``37``.
    sim_noise : bool, optional
        Enable noise simulation. Defaults to ``False``.
    scan_map : bool, optional
        Enable sky map scanning. Defaults to ``False``.
    sim_atmosphere : bool, optional
        Enable atmosphere simulation. Defaults to ``False``.
    sim_sss : bool, optional
        Enable spin-synchronous signal simulation. Defaults to ``False``.
    sim_hwpss : bool, optional
        Enable HWP synchronous signal simulation. Defaults to ``False``.
    sim_hwpss_atmo_data : str or None, optional
        Path to HWPSS atmosphere data file. Maps to the TOAST argument
        ``sim_hwpss.atmo_data``.
    pixels_healpix_radec_nside : int, optional
        HEALPix ``nside`` parameter for the output map. Maps to the TOAST
        argument ``pixels_healpix_radec.nside``. Defaults to ``512``.
    filterbin_name : str or None, optional
        Filter-bin output name. Maps to ``filterbin.name``.
    processing_mask_file : str or None, optional
        Path to the processing mask file. Maps to ``processing_mask.file``.
    """

    output_dir: str
    name: str = "sat_sims"
    executable: str = "toast_so_sim"
    schedule: str | None = None
    bands: str | None = "SAT_f090"
    wafer_slots: str | None = "w25"
    sample_rate: int = 37
    sim_noise: bool = False
    scan_map: bool = False
    sim_atmosphere: bool = False
    sim_sss: bool = False
    sim_hwpss: bool = False
    sim_hwpss_atmo_data: str | None = None
    pixels_healpix_radec_nside: int = 512
    filterbin_name: str | None = None
    processing_mask_file: str | None = None

    _arg_translation: dict[str, str] = PrivateAttr(
        {
            "sim_hwpss_atmo_data": "sim_hwpss.atmo_data",
            "pixels_healpix_radec_nside": "pixels_healpix_radec.nside",
            "filterbin_name": "filterbin.name",
            "processing_mask_file": "processing_mask.file",
        }
    )

    def get_command(self, **kargs: Any) -> str:
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

    def get_arguments(self, **kargs: Any) -> list[str]:
        """One entry per argument, without shell quoting."""
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
