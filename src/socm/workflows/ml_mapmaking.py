from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Union

from sotodlib.core import Context

from socm.core import Workflow
from socm.utils.misc import get_query_from_file


@lru_cache(maxsize=10)
def _load_context(ctx_path: str) -> Context:
    return Context(Path(ctx_path))


class MLMapmakingWorkflow(Workflow):
    """
    Workflow for maximum-likelihood (ML) mapmaking via ``so-site-pipeline make-ml-map``.

    On construction the sotodlib observation database is queried to compute the
    total data size (``datasize``) for use by the planner's resource estimator.
    Query strings may be provided inline or as ``file://`` URIs pointing to
    plain-text files containing one observation ID per line.

    Parameters
    ----------
    area : str
        Path (or ``file://`` URI) to the FITS sky-area file.
    output_dir : str
        Directory where mapmaking products will be written.
    preprocess_config : str
        Path (or ``file://`` URI) to the preprocessing configuration file.
    query : str, optional
        SQL-style observation database query string, or a ``file://`` URI to a
        file containing one observation ID per line. Defaults to ``"1"``
        (select all observations).
    name : str, optional
        Human-readable workflow name. Defaults to ``"ml_mapmaking_workflow"``.
    executable : str, optional
        Executable name. Defaults to ``"so-site-pipeline"``.
    subcommand : str, optional
        Subcommand passed to the executable. Defaults to ``"make-ml-map"``.
    datasize : int, optional
        Total number of data samples across all selected observations. Computed
        automatically during post-initialisation; can also be set explicitly.
        Defaults to ``0``.
    comps : str or None, optional
        Map components to produce (e.g. ``"TQU"`` or ``"T"``). Defaults to
        ``"TQU"``.
    wafers : str or None, optional
        Comma-separated list of detector wafers to include. ``None`` means all.
    bands : str or None, optional
        Frequency band filter string. ``None`` means all bands.
    nmat : str or None, optional
        Noise-matrix model identifier (e.g. ``"corr"``). Defaults to
        ``"corr"``.
    max_dets : int or None, optional
        Maximum number of detectors to use. ``None`` means no limit.
    site : str or None, optional
        Telescope site identifier (e.g. ``"so_lat"``). Defaults to
        ``"so_lat"``.
    downsample : int or list of int, optional
        Downsampling factor(s). Defaults to ``1``.
    maxiter : int or list of int, optional
        Maximum conjugate-gradient iterations. Defaults to ``500``.
    tiled : int, optional
        Enable tiled mapmaking (``1``) or not (``0``). Defaults to ``1``.
    """

    area: str
    output_dir: str
    preprocess_config: str
    query: str = "1"
    name: str = "ml_mapmaking_workflow"
    executable: str = "so-site-pipeline"
    subcommand: str = "make-ml-map"
    datasize: int = 0
    comps: Optional[str] = "TQU"
    wafers: Optional[str] = None
    bands: Optional[str] = None
    nmat: Optional[str] = "corr"
    max_dets: Optional[int] = None
    site: Optional[str] = "so_lat"
    downsample: Union[int, List[int]] = 1
    maxiter: Union[int, List[int]] = 500
    tiled: int = 1

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialisation hook that queries the observation database to compute ``datasize``.

        Loads the sotodlib :class:`~sotodlib.core.Context` from the ``context``
        field, resolves the query (inline string or ``file://`` path), and
        accumulates ``n_samples`` from each matching observation into
        :attr:`datasize`.

        Parameters
        ----------
        __context : Any
            Pydantic internal context argument (not used directly).
        """
        ctx_file = Path(self.context.split("file://")[-1]).absolute()
        ctx = _load_context(str(ctx_file))

        final_query = self.query
        if self.query.startswith("file://"):
            query_path = Path(self.query.split("file://")[-1]).absolute()
            final_query = get_query_from_file(query_path)
        obs_ids = ctx.obsdb.query(final_query)
        for obs_id in obs_ids:
            self.datasize += obs_id["n_samples"]

    def get_command(self) -> str:
        """
        Build the full ``srun`` command string for the ML mapmaking workflow.

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
        Build the list of command-line arguments for the ML mapmaking workflow.

        Constructs a positional argument list followed by ``--key=value``
        options for every field set in the workflow configuration that is not
        part of the excluded set (``area``, ``output_dir``, ``executable``,
        ``query``, ``id``, ``environment``, ``resources``, ``datasize``,
        ``preprocess_config``).

        ``file://`` URI values are resolved to absolute paths. List values are
        joined with commas.

        Returns
        -------
        list of str
            Ordered list of positional and keyword argument strings.
        """
        area = Path(self.area.split("file://")[-1])
        final_query = self.query
        if self.query.startswith("file://"):
            final_query = Path(self.query.split("file://")[-1]).absolute()
            final_query = f"{final_query.absolute()}"
        preprocess_config = Path(self.preprocess_config.split("file://")[-1])

        arguments = [final_query, f"{area.absolute()}", self.output_dir, f"{preprocess_config.absolute()}"]
        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
            elif isinstance(v, list):
                v = ",".join([str(item) for item in v])
            if k not in [
                "area",
                "output_dir",
                "executable",
                "query",
                "output_dir",
                "id",
                "environment",
                "resources",
                "datasize",
                "preprocess_config"
            ]:
                arguments.append(f"--{k}={v}")
        return arguments

    @classmethod
    def get_workflows(
        cls, descriptions: Union[List[dict], dict]
    ) -> List["MLMapmakingWorkflow"]:
        """
        Create :class:`MLMapmakingWorkflow` instances from configuration descriptions.

        Parameters
        ----------
        descriptions : dict or list of dict
            A single workflow configuration dictionary or a list of them.
            Each dictionary is passed as keyword arguments to the constructor.

        Returns
        -------
        list of MLMapmakingWorkflow
            One instantiated workflow per configuration dictionary.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]

        workflows = []
        for desc in descriptions:
            workflow = cls(**desc)
            workflows.append(workflow)

        return workflows
