from datetime import timedelta
from pathlib import Path

import numpy as np
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class TimeNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for time null tests.
    """

    chunk_nobs: int | None = None
    chunk_duration: timedelta | None = None
    nsplits: int = 8
    name: str = "time_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: dict[str, dict[str, float | str]]
    ) -> list[list[str]]:
        """
        Distribute the observations across splits based on the context and observation IDs.
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
    def get_workflows(cls, desc=None) -> list[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.
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
                f.writelines(f"{oid}\n" for oid in split)
            desc["query"] = f"file://{query_file.absolute()!s}"
            desc["chunk_nobs"] = 1
            workflow = NullTestWorkflow(**desc)
            workflows.append(workflow)

        return workflows
