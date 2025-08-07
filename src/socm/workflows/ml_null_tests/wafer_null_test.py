from datetime import timedelta
from typing import Dict, List, Optional, Union

import numpy as np
from pydantic import PrivateAttr
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class WaferNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for time null tests.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 8
    name: str = "wafer_null_test_workflow"

    _wafer_list_per_telescope: Dict[str, List[str]] = PrivateAttr(
        {
            "sat": [
                "st1:ws0",
                "st1:ws1",
                "st1:ws2",
                "st1:ws3",
                "st1:ws4",
                "st1:ws5",
                "st1:ws6",
            ],
            "act": ["st1:ws0"],
            "lat": [
                "c1:ws0",
                "c1:ws1",
                "c1:ws2",
                "i1:ws0",
                "i1:ws1",
                "i1:ws2",
                "i2:ws0",
                "i2:ws1",
                "i2:ws2",
                "i3:ws0",
                "i3:ws1",
                "i3:ws2",
                "i4:ws0",
                "i4:ws1",
                "i4:ws2",
                "i5:ws0",
                "i5:ws1",
                "i5:ws2",
                "i6:ws0",
                "i6:ws1",
                "i6:ws2",
            ],
        }
    )

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[str]]:
        """
        Distribute the observations across splits based on the context and observation IDs.
        """
        # Find the obs with the most wafers.
        # For each wafer do the same as the time null test.
        if self.chunk_nobs is None and self.chunk_duration is None:
            raise ValueError("Either chunk_nobs or duration must be set.")
        elif self.chunk_nobs is not None and self.chunk_duration is not None:
            raise ValueError("Only one of chunk_nobs or duration can be set.")
        elif self.chunk_nobs is None:
            # Decide the chunk size based on the duration. Each chunk needs to have the
            # observataions that their start times are just less than chunk_duration.
            raise NotImplementedError(
                "Splitting by duration is not implemented yet. Please set chunk_nobs."
            )

        tube_slots = set([v["tube_slot"] for v in obs_info.values()])
        if len(tube_slots) != 1:
            raise ValueError(
                f"All observations must be from the same tube slot. Found: {tube_slots}"
            )
        final_splits = {}
        for tube_wafer in self._wafer_list_per_telescope[self.site]:
            tube_slot, wafer = tube_wafer.split(":")
            wafer_obs_info = dict()
            for k, v in obs_info.items():
                if (
                    v["wafer_list"] is not None
                    and v["tube_slot"] is not None
                    and wafer in v["wafer_list"]
                    and tube_slot in v["tube_slot"]
                ):
                    wafer_obs_info[k] = v
            if not wafer_obs_info:
                continue
            sorted_ids = sorted(
                wafer_obs_info, key=lambda k: wafer_obs_info[k]["start_time"]
            )
            # Group in chunks of size self.chunk_nobs observations.
            num_chunks = (
                len(sorted_ids) + self.chunk_nobs - 1
            ) // self.chunk_nobs  # Ceiling division
            obs_lists = np.array_split(sorted_ids, num_chunks)
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()
            final_splits[tube_wafer] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.
        """

        wafer_workflow = cls(**desc)

        workflows = []
        for tube_wafer, wafer_split in wafer_workflow._splits.items():
            _, wafer = tube_wafer.split(":")
            for idx, split in enumerate(wafer_split):
                desc = wafer_workflow.model_dump(exclude_unset=True)
                desc["name"] = f"wafer_{wafer}_split_{idx + 1}_null_test_workflow"
                desc["datasize"] = 0
                desc["query"] = "obs_id IN ("
                for oid in split:
                    desc["query"] += f"'{oid}',"
                desc["query"] = desc["query"].rstrip(",")
                desc["query"] += ")"
                desc["chunk_nobs"] = 1
                desc["wafer"] = wafer
                desc["output_dir"] = (
                    f"{wafer_workflow.output_dir}/wafer_{wafer}_split_{idx + 1}"
                )
                workflow = NullTestWorkflow(**desc)
                workflows.append(workflow)

        return workflows
