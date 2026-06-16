from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sotodlib.core import Context

from socm.utils.misc import get_query_from_file
from socm.workflows import MLMapmakingWorkflow


class NullTestWorkflow(MLMapmakingWorkflow):
    """
    Base class for all null-test workflows.

    Extends :class:`~socm.workflows.ml_mapmaking.MLMapmakingWorkflow` with
    observation-splitting logic. After Pydantic validation (via
    :meth:`model_post_init`) the observation database is queried, metadata is
    collected for each matching observation, and :meth:`_get_splits` is called
    to divide the observations into sets. Each set is later turned into an
    independent workflow instance by the :meth:`get_workflows` class method.

    Subclasses must override :meth:`_get_splits` to implement the specific
    splitting criterion (time, wafer, direction, etc.) and :meth:`get_workflows`
    to instantiate one child workflow per resulting split.

    Parameters
    ----------
    area : str
        Path (or ``file://`` URI) to the FITS sky-area file.
    output_dir : str
        Root output directory; each split writes to a subdirectory.
    query : str, optional
        Observation-database query string or ``file://`` URI. Defaults to
        ``"1"`` (all observations).
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"lat_null_test_workflow"``.
    datasize : int, optional
        Accumulated sample count (computed automatically). Defaults to ``0``.
    chunk_nobs : int or None, optional
        Number of observations per time chunk used by splitting subclasses.
        Exactly one of ``chunk_nobs`` and ``chunk_duration`` must be set.
        Defaults to ``None``.
    chunk_duration : timedelta or None, optional
        Duration per time chunk (not yet fully supported in all subclasses).
        Defaults to ``None``.
    """

    area: str
    output_dir: str
    query: str = "1"
    name: str = "lat_null_test_workflow"
    datasize: int = 0
    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialisation hook that queries the observation database and computes splits.

        Loads the sotodlib :class:`~sotodlib.core.Context`, resolves the query
        string, collects per-observation metadata (timestamp, wafers, tube slot,
        azimuth, elevation, PWV, throw, duration, sample count), and calls
        :meth:`_get_splits` to produce the observation splits stored in
        :attr:`_splits`.

        Parameters
        ----------
        __context : Any
            Pydantic internal context argument (not used directly).
        """
        ctx_file = Path(self.context.split("file://")[-1]).absolute()
        ctx = Context(ctx_file)
        final_query = self.query
        if self.query.startswith("file://"):
            query_path = Path(self.query.split("file://")[-1]).absolute()
            final_query = get_query_from_file(query_path)
        obs_ids = ctx.obsdb.query(final_query)
        obs_info = dict()
        for obs_id in obs_ids:
            self.datasize += obs_id["n_samples"]
            obs_info[obs_id["obs_id"]] = {
                "start_time": float(obs_id["timestamp"]),
                "wafer_list": obs_id["wafer_slots_list"].split(","),
                "tube_slot": obs_id.get("tube_slot", "st1"),
                "az_center": float(obs_id["az_center"]),
                "el_center": float(obs_id["el_center"]),
                "pwv": obs_id.get("pwv", 0),
                "az_throw": float(obs_id.get("az_throw", 30.0)),
                "duration": float(obs_id.get("duration", 600.0)),
                "n_samples": int(obs_id["n_samples"]),
            }
        # Ensure obs_ids are sorted by their timestamp
        # Order the obs_ids based on their timestamp it is in the obs_meta.obs_info.timestamp

        self._splits = self._get_splits(ctx, obs_info)

    def _get_num_chunks(self, num_obs: int) -> int:
        """
        Compute the number of time chunks for a given observation count.

        Uses ceiling division so that no observation is dropped.

        Parameters
        ----------
        num_obs : int
            The total number of observations to chunk.

        Returns
        -------
        int
            The number of chunks needed to cover ``num_obs`` observations
            with at most ``chunk_nobs`` observations per chunk.
        """
        num_chunks = (
            num_obs + self.chunk_nobs - 1
        ) // self.chunk_nobs  # Ceiling division
        return num_chunks

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> List[List[str]]:
        """
        Compute observation splits for the null test.

        Must be implemented by every concrete subclass. The base implementation
        raises :class:`NotImplementedError` when called on any class other than
        ``NullTestWorkflow`` itself (which uses a no-op pass for the base case).

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object.
        obs_info : dict of str to dict
            Mapping of observation ID to its metadata dictionary containing
            keys ``start_time``, ``wafer_list``, ``tube_slot``, ``az_center``,
            ``el_center``, ``pwv``, ``az_throw``, ``duration``, and
            ``n_samples``.

        Returns
        -------
        list of list of str or dict
            The observation splits. The exact structure depends on the
            subclass: most return a ``list`` of splits (each a list of obs
            IDs), while some return a ``dict`` mapping a category label to a
            list of splits.

        Raises
        ------
        NotImplementedError
            Raised by any concrete subclass that has not overridden this method.
        """
        if self.__class__.__name__ != "NullTestWorkflow":
            raise NotImplementedError(
                "This method should be implemented in subclasses."
            )
        else:
            pass

    @classmethod
    def get_workflows(cls, desc: Dict[str, Any]) -> List["NullTestWorkflow"]:
        """
        Create :class:`NullTestWorkflow` instances from a configuration description.

        Must be implemented by every concrete subclass. The base implementation
        raises :class:`NotImplementedError` when called on any class other than
        ``NullTestWorkflow`` itself.

        Parameters
        ----------
        desc : dict
            The workflow configuration dictionary passed as keyword arguments
            to the constructor.

        Returns
        -------
        list of NullTestWorkflow
            One workflow instance per non-empty observation split.

        Raises
        ------
        NotImplementedError
            Raised by any concrete subclass that has not overridden this method.
        """
        if cls.__name__ != "NullTestWorkflow":
            raise NotImplementedError(
                "This method should be implemented in subclasses."
            )
        else:
            pass

    def get_arguments(self) -> List[str]:
        """
        Build the list of command-line arguments for the null-test workflow.

        Constructs positional arguments (query file path, area, output
        directory, preprocessing config) followed by ``--key=value`` options
        for every set field not in the exclusion list (``area``,
        ``output_dir``, ``executable``, ``query``, ``id``, ``environment``,
        ``resources``, ``datasize``, ``chunk_nobs``, ``nsplits``, ``wafers``,
        ``subcommand``, ``name``, ``chunk_duration``, ``preprocess_config``).

        ``file://`` URIs are resolved to absolute paths. List values are joined
        with commas.

        Returns
        -------
        list of str
            Ordered list of positional and keyword argument strings.
        """
        area = Path(self.area.split("file://")[-1])
        query = Path(self.query.split("file://")[-1])
        preprocess_config = Path(self.preprocess_config.split("file://")[-1])

        arguments = [f"{query.absolute()}", f"{area.absolute()}", self.output_dir, f"{preprocess_config.absolute()}"]
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
                "id",
                "environment",
                "resources",
                "datasize",
                "chunk_nobs",
                "nsplits",
                "wafers",
                "subcommand",
                "name",
                "chunk_duration",
                "preprocess_config"
            ]:
                arguments.append(f"--{k}={v}")
        return arguments
