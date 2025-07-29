from datetime import timedelta
from typing import Dict, List, Optional, Union

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class PWVNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for direction null tests.

    This workflow splits observations based on scan direction (rising, setting, middle)
    and creates time-interleaved splits with nsplits=2 as specified.
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
        Distribute the observations across splits based on scan direction.

        Groups observations by direction (rising, setting, middle) and then
        creates time-interleaved splits for each direction with nsplits=2.

        Args:
            ctx: Context object
            obs_info: Dictionary mapping obs_id to observation metadata

        Returns:
            Dict mapping direction to list of splits, where each split is a list
            of obs_ids
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
            obs_lists = np.array_split(sorted_ids, self.chunk_nobs)

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[pwv_level] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.

        Creates separate workflows for each direction split following the naming
        convention: {setname} = direction_[rising,setting,middle]
        """
        pwv_workflow = cls(**desc)

        workflows = []
        for pwv_level, pwv_splits in pwv_workflow._splits.items():
            for split_idx, split in enumerate(pwv_splits):
                desc_copy = pwv_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"pwv_{pwv_level}_split_{split_idx + 1}_null_test_workflow"
                )
                desc_copy["datasize"] = 0
                desc_copy["query"] = "obs_id IN ("
                for oid in split:
                    desc_copy["query"] += f"'{oid}',"
                desc_copy["query"] = desc_copy["query"].rstrip(",")
                desc_copy["query"] += ")"
                desc_copy["chunk_nobs"] = 1

                # Follow the naming convention: pwv_[high,low]
                desc_copy["output_dir"] = (
                    f"{pwv_workflow.output_dir}/pwv_{pwv_level}_split_{split_idx + 1}"
                )

                workflow = NullTestWorkflow(**desc_copy)
                workflows.append(workflow)

        return workflows
