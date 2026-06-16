from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class PWVNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by precipitable water vapour (PWV).

    Classifies each observation as ``"high"`` (PWV > ``pwv_limit``) or
    ``"low"`` (PWV ≤ ``pwv_limit``), then within each group creates
    ``nsplits = 2`` time-interleaved splits to test for atmosphere-dependent
    systematics. Child workflows follow the naming convention
    ``pwv_<level>_split_<N>_null_test_workflow``.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk per PWV group. Defaults to
        ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk (not yet implemented). Defaults to ``None``.
    pwv_limit : float, optional
        PWV threshold in mm. Observations above this value are classified as
        ``"high"``. Defaults to ``2.0``.
    nsplits : int, optional
        Number of time splits per PWV group. Fixed to ``2``. Defaults to ``2``.
    name : str, optional
        Human-readable workflow name. Defaults to ``"pwv_null_test_workflow"``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    pwv_limit: float = 2.0  # Example limit for PWV, adjust as needed
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "pwv_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Distribute observations into PWV-level-based, time-interleaved splits.

        Groups observations by whether their PWV exceeds ``pwv_limit``. Within
        each group, observations are sorted chronologically, chunked by
        ``chunk_nobs``, and assigned round-robin to ``nsplits`` (= 2) splits.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``pwv`` and
            ``start_time`` keys are used.

        Returns
        -------
        dict of str to list of list of str
            Mapping of PWV level (``"high"`` or ``"low"``) to a list of
            ``nsplits`` splits, each containing the observation IDs assigned
            to that level and split.

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

        # Group observations by scan direction
        pwv_splits = {"high": [], "low": []}
        for obs_id, obs_meta in obs_info.items():
            if obs_meta["pwv"] > self.pwv_limit:
                pwv_splits["high"].append(obs_id)
            else:
                pwv_splits["low"].append(obs_id)

        final_splits = {}

        # For each pwv level, create time-interleaved splits
        for pwv_level, pwv_obs_info in pwv_splits.items():
            if not pwv_obs_info:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(pwv_obs_info, key=lambda k: obs_info[k]["start_time"])

            # Group in chunks based on chunk_nobs
            num_chunks = self._get_num_chunks(len(sorted_ids))
            obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[pwv_level] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per PWV-split pair.

        Instantiates the parent :class:`PWVNullTestWorkflow` to compute the
        splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty (PWV level, time-split) combination. Query files are written
        to ``<output_dir>/pwv_<level>_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty PWV-split pair, named
            ``pwv_<level>_split_<N>_null_test_workflow``.
        """
        pwv_workflow = cls(**desc)

        workflows = []
        for pwv_level, pwv_splits in pwv_workflow._splits.items():
            for split_idx, split in enumerate(pwv_splits):
                if not split:
                    continue
                desc_copy = pwv_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"pwv_{pwv_level}_split_{split_idx + 1}_null_test_workflow"
                )

                # Follow the naming convention: pwv_[high,low]
                desc_copy["output_dir"] = (
                    f"{pwv_workflow.output_dir}/pwv_{pwv_level}_split_{split_idx + 1}"
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
