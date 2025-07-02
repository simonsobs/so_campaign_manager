from datetime import timedelta
import numpy as np
from typing import List, Optional

from sotodlib.core import Context

from socm.workflows.lat_null_tests import NullTestWorkflow


class TimeNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for time null tests.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 8

    def _get_splits(self, ctx: Context, obs_ids: List[str]) -> List[List[str]]:
        """
        Distribute the observations across splits based on the context and observation IDs.
        """
        if self.chunk_nobs is None and self.chunk_duration is None:
            raise ValueError("Either chunk_nobs or duration must be set.")
        elif self.chunk_nobs is not None and self.chunk_duration is not None:
            raise ValueError("Only one of chunk_nobs or duration can be set.")
        elif self.chunk_nobs is None:
            # Decide the chunk size based on the duration. Each chunk needs to have the
            # observataions that their start times are just less than chunk_duration.
            raise NotImplementedError("Splitting by duration is not implemented yet. Please set chunk_nobs.")

        # Group in chunks of 10 observations.
        obs_lists = np.array_split(obs_ids, self.chunk_nobs)
        splits = [""] * self.nsplits
        for i, obs_list in enumerate(obs_lists):
            splits[i % self.nsplits] += ",".join(obs_list) + " "

        return splits
