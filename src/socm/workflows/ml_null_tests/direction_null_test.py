from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class DirectionNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by scan direction.

    Classifies each observation into one of three azimuth categories —
    ``"rising"`` (az < 180°), ``"setting"`` (az > 180°), or ``"middle"``
    (az ≈ 180°) — then within each direction creates ``nsplits = 2``
    time-interleaved splits. The split structure follows the naming convention
    ``direction_<direction>_split_<N>_null_test_workflow``.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk per direction. Defaults to
        ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk (not yet implemented). Defaults to ``None``.
    nsplits : int, optional
        Number of time splits per direction. Fixed to ``2``. Defaults to ``2``.
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"direction_null_test_workflow"``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "direction_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Distribute observations into direction-based, time-interleaved splits.

        Groups observations by azimuth center into ``"rising"``,
        ``"setting"``, or ``"middle"`` categories. Within each category,
        observations are sorted chronologically, chunked by ``chunk_nobs``,
        and assigned round-robin to ``nsplits`` (= 2) splits.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``az_center`` and
            ``start_time`` keys are used.

        Returns
        -------
        dict of str to list of list of str
            Mapping of direction name to a list of ``nsplits`` splits, each
            containing the observation IDs assigned to that direction and split.

        Raises
        ------
        ValueError
            If neither ``chunk_nobs`` nor ``chunk_duration`` is set, if both
            are set, or if an unexpected azimuth value is encountered.
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

        # Group observations by scan direction
        direction_splits = {"rising": [], "setting": [], "middle": []}
        for obs_id, obs_meta in obs_info.items():
            if np.isclose(
                obs_meta["az_center"] % 360, 180
            ):  # Azimuth close to 180 is considered 'middle'
                direction = "middle"
            elif (
                obs_meta["az_center"] % 360
            ) > 180:  # More than 180 degrees is considered 'setting'
                direction = "setting"
            elif (
                obs_meta["az_center"] % 360
            ) < 180:  # Less than 180 degrees is considered 'rising'
                direction = "rising"
            else:
                raise ValueError(
                    f"Unknown azimuth center value for {obs_id}: {obs_meta['az_center']}"
                )

            if direction in direction_splits:
                direction_splits[direction].append(obs_id)

        final_splits = {}

        # For each direction, create time-interleaved splits
        for direction, direction_obs_info in direction_splits.items():
            if not direction_obs_info:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(
                direction_obs_info, key=lambda k: obs_info[k]["start_time"]
            )

            # Group in chunks based on chunk_nobs
            num_chunks = self._get_num_chunks(len(sorted_ids))
            obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[direction] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per direction-split pair.

        Instantiates the parent :class:`DirectionNullTestWorkflow` to compute
        the splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty (direction, time-split) combination. Query files are written
        to ``<output_dir>/direction_<direction>_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty direction-split pair, named
            ``direction_<direction>_split_<N>_null_test_workflow``.
        """
        direction_workflow = cls(**desc)

        workflows = []
        for direction, direction_splits in direction_workflow._splits.items():
            for split_idx, split in enumerate(direction_splits):
                if not split:
                    continue
                desc_copy = direction_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"direction_{direction}_split_{split_idx + 1}_null_test_workflow"
                )
                desc_copy["datasize"] = 0
                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{direction_workflow.output_dir}/direction_{direction}_split_{split_idx + 1}"
                )
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
