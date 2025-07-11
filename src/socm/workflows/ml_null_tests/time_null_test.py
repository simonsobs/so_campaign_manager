from datetime import timedelta
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class TimeNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for time null tests.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 8
    name: str = "time_null_test_workflow"

    def _get_splits(self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]) -> List[List[str]]:
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
        sorted_ids = sorted(obs_info, key=lambda k: obs_info[k]["start_time"])
        # Group in chunks of 10 observations.
        obs_lists = np.array_split(sorted_ids, self.chunk_nobs)
        splits = [[] for _ in range(self.nsplits)]
        for i, obs_list in enumerate(obs_lists):
            splits[i % self.nsplits] += obs_list.tolist()

        return splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.
        """

        time_workflow = cls(**desc)

        workflows = []
        for split in time_workflow._splits:
            desc = time_workflow.model_dump(exclude_unset=True)
            desc["datasize"] = 0
            desc["query"] = "obs_id IN ("
            for oid in split:
                desc["query"] += f"'{oid}',"
            desc["query"] = desc["query"].rstrip(",")
            desc["query"] += ")"
            desc["chunk_nobs"] = 1
            desc["output_dir"] = f"{time_workflow.output_dir}/mission_split_{len(workflows) + 1}"
            workflow = NullTestWorkflow(**desc)
            workflows.append(workflow)

        return workflows
