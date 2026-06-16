from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import PrivateAttr

from ..core.models import Workflow


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

    def get_command(self, **kargs: Any) -> str:
        """
        Build the full ``srun`` command string for the SAT simulation workflow.

        Constructs an ``srun`` invocation using the resource specification
        (``ranks``, ``threads``) and appends all arguments from
        :meth:`get_arguments`.

        Returns
        -------
        str
            The complete shell command string, stripped of trailing whitespace.

        Raises
        ------
        ValueError
            If :attr:`resources` is ``None`` (i.e. has not been set yet).
        """
        if self.resources is None:
            raise ValueError("Resources must be set before calling get_command")
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={self.resources.ranks} --cpus-per-task={self.resources.threads} {self.executable} {self.subcommand} --job_group_size={self.resources.ranks} "
        command += self.get_arguments()

        return command.strip()

    def get_arguments(self, **kargs: Any) -> str:
        """
        Build the argument string for the SAT simulation workflow.

        Iterates over all set fields (excluding meta-fields such as ``name``,
        ``id``, ``resources``, etc.) and constructs TOAST-style arguments.
        Boolean fields are rendered as ``--field.enable`` / ``--field.disable``.
        Field names that appear in the internal translation table are mapped to
        their dotted TOAST equivalents.  ``file://`` URIs are resolved to
        absolute paths.

        Returns
        -------
        str
            A single space-separated argument string suitable for appending to
            the command returned by :meth:`get_command`.
        """
        arguments = f"--out {self.output_dir} "
        sorted_workflow = dict(sorted(self.model_dump().items()))

        for k, v in sorted_workflow.items():
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
            if k not in [
                "name",
                "output_dir",
                "executable",
                "id",
                "environment",
                "resources",
                "depends",
            ]:
                if isinstance(v, bool):
                    if v:
                        arguments += f"--{k}.enable "
                    else:
                        arguments += f"--{k}.disable "
                else:
                    arguments += f"--{self._arg_translation.get(k, k)}={v} "
        return arguments.strip()
