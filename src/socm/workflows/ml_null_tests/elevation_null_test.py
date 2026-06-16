from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class ElevationNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by telescope elevation.

    Classifies each observation as ``"low"`` (elevation < ``elevation_threshold``)
    or ``"high"`` (elevation ≥ ``elevation_threshold``), then within each group
    creates ``nsplits = 2`` time-interleaved splits to test for
    elevation-dependent systematics such as ground pickup or atmospheric
    gradients. Child workflows follow the naming convention
    ``elevation_<level>_split_<N>_null_test_workflow``.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk per elevation group. Defaults to
        ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk (not yet implemented). Defaults to ``None``.
    nsplits : int, optional
        Number of time splits per elevation group. Fixed to ``2``. Defaults to
        ``2``.
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"elevation_null_test_workflow"``.
    elevation_threshold : float, optional
        Elevation threshold in degrees. Observations with an elevation centre
        below this value are classified as ``"low"``. Defaults to ``45.0``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "elevation_null_test_workflow"
    elevation_threshold: float = 45.0  # Elevation threshold in degrees

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Distribute observations into elevation-based, time-interleaved splits.

        Groups observations by whether their elevation centre is below or above
        ``elevation_threshold``. Within each group, observations are sorted
        chronologically, chunked by ``chunk_nobs``, and assigned round-robin
        to ``nsplits`` (= 2) splits.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``el_center`` and
            ``start_time`` keys are used.

        Returns
        -------
        dict of str to list of list of str
            Mapping of elevation label (``"low"`` or ``"high"``) to a list of
            ``nsplits`` splits, each containing the observation IDs assigned
            to that elevation group and split.

        Raises
        ------
        ValueError
            If neither ``chunk_nobs`` nor ``chunk_duration`` is set, or if
            both are set.
        NotImplementedError
            If ``chunk_duration`` is set (not yet implemented).
        """
        if self.chunk_nobs is None and self.chunk_duration is None:
            raise ValueError("Either chunk_nobs or duration must be set.")
        elif self.chunk_nobs is not None and self.chunk_duration is not None:
            raise ValueError("Only one of chunk_nobs or duration can be set.")
        elif self.chunk_nobs is None:
            # Decide the chunk size based on the duration
            raise NotImplementedError(
                "Splitting by duration is not implemented yet. Please set chunk_nobs."
            )

        # Group observations by elevation angles
        elevation_splits = {"low": [], "high": []}
        for obs_id, obs_meta in obs_info.items():
            if obs_meta["el_center"] < self.elevation_threshold:
                elevation_splits["low"].append(obs_id)
            else:
                elevation_splits["high"].append(obs_id)

        final_splits = {}

        # For each elevation, create time-interleaved splits
        for elevation, obs_infos in elevation_splits.items():
            if not obs_infos:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(obs_infos, key=lambda k: obs_info[k]["start_time"])

            # Group in chunks based on chunk_nobs
            num_chunks = self._get_num_chunks(len(sorted_ids))
            obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[elevation] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per elevation-split pair.

        Instantiates the parent :class:`ElevationNullTestWorkflow` to compute
        the splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty (elevation label, time-split) combination. Query files are
        written to ``<output_dir>/elevation_<level>_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty elevation-split pair, named
            ``elevation_<level>_split_<N>_null_test_workflow``.
        """
        elevation_workflow = cls(**desc)

        workflows = []
        for elevation, elevation_splits in elevation_workflow._splits.items():
            for split_idx, split in enumerate(elevation_splits):
                if not split:
                    continue
                desc_copy = elevation_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"elevation_{elevation}_split_{split_idx + 1}_null_test_workflow"
                )

                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{elevation_workflow.output_dir}/elevation_{elevation}_split_{split_idx + 1}"
                )
                desc_copy["datasize"] = 0
                query_file = Path(desc_copy["output_dir"]) / "query.txt"
                query_file.parent.mkdir(parents=True, exist_ok=True)
                with open(query_file, "w") as f:
                    for oid in split:
                        f.write(f"{oid}\n")
                desc_copy["query"] = f"file://{str(query_file.absolute())}"
                desc_copy["chunk_nobs"] = 1
                workflow = NullTestWorkflow(**desc_copy)
                workflows.append(workflow)

        return workflows
