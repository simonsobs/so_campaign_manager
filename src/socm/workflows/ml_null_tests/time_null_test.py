from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class TimeNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by mission time (temporal null test).

    Observations are sorted chronologically, grouped into chunks of
    ``chunk_nobs`` observations each, and then distributed across
    ``nsplits`` splits in a round-robin (time-interleaved) fashion so that
    each split covers the full mission span.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk. Exactly one of ``chunk_nobs``
        and ``chunk_duration`` must be set. Defaults to ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk. Not yet implemented; raises
        :class:`NotImplementedError` if set without ``chunk_nobs``. Defaults
        to ``None``.
    nsplits : int, optional
        Number of splits (sub-campaigns) to produce. Defaults to ``8``.
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"time_null_test_workflow"``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 8
    name: str = "time_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> List[List[str]]:
        """
        Distribute observations across splits in a time-interleaved fashion.

        Observations are sorted by start time, grouped into chunks of
        ``chunk_nobs``, and distributed round-robin across ``nsplits`` splits.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly but required by the interface).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``start_time`` key is
            used for chronological ordering.

        Returns
        -------
        list of list of str
            A list of ``nsplits`` splits, each containing the observation IDs
            assigned to that split.

        Raises
        ------
        ValueError
            If neither ``chunk_nobs`` nor ``chunk_duration`` is set, or if
            both are set simultaneously.
        NotImplementedError
            If ``chunk_duration`` is set (duration-based splitting is not yet
            implemented).
        """
        if self.chunk_nobs is None and self.chunk_duration is None:
            raise ValueError("Either chunk_nobs or duration must be set.")
        elif self.chunk_nobs is not None and self.chunk_duration is not None:
            raise ValueError("Only one of chunk_nobs or duration can be set.")
        elif self.chunk_nobs is None:
            # Decide the chunk size based on the duration. Each chunk needs to have the
            # observations that their start times are just less than chunk_duration.
            raise NotImplementedError(
                "Splitting by duration is not implemented yet. Please set chunk_nobs."
            )

        sorted_ids = sorted(obs_info, key=lambda k: obs_info[k]["start_time"])
        # Group in chunks of size self.chunk_nobs observations.
        num_chunks = self._get_num_chunks(len(sorted_ids))
        obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []
        splits = [[] for _ in range(self.nsplits)]
        for i, obs_list in enumerate(obs_lists):
            splits[i % self.nsplits] += obs_list.tolist()

        return splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per non-empty time split.

        Instantiates the parent :class:`TimeNullTestWorkflow` to compute the
        splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty split. Query files containing the assigned observation IDs are
        written to ``<output_dir>/mission_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty split, named
            ``mission_split_<N>_null_test_workflow``.
        """

        time_workflow = cls(**desc)

        workflows = []
        for split in time_workflow._splits:
            if not split:
                continue
            desc = time_workflow.model_dump(exclude_unset=True)
            desc["name"] = f"mission_split_{len(workflows) + 1}_null_test_workflow"
            desc["output_dir"] = (
                f"{time_workflow.output_dir}/mission_split_{len(workflows) + 1}"
            )
            desc["datasize"] = 0
            query_file = Path(desc["output_dir"]) / "query.txt"
            query_file.parent.mkdir(parents=True, exist_ok=True)
            with open(query_file, "w") as f:
                for oid in split:
                    f.write(f"{oid}\n")
            desc["query"] = f"file://{str(query_file.absolute())}"
            desc["chunk_nobs"] = 1
            workflow = NullTestWorkflow(**desc)
            workflows.append(workflow)

        return workflows
