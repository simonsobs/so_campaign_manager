from pathlib import Path
from typing import Any, Dict, List

from sotodlib.core import Context
from socm.workflows import MLMapmakingWorkflow


class NullTestWorkflow(MLMapmakingWorkflow):
    """
    A workflow for null tests.
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
        Post-initialization to set the context for the workflow and distribute the
        observations across splits.
        """
        ctx_file = Path(self.context.split("file://")[-1]).absolute()
        ctx = Context(ctx_file)
        obs_ids = ctx.obsdb.query(self.query)["obs_id"]
        obs_info = dict()
        for obs_id in obs_ids:
            obs_meta = ctx.get_meta(obs_id)
            self.datasize += obs_meta.samps.count
            obs_info[obs_id] = {
                "start_time": obs_meta.obs_info.timestamp.start,
                "wafer_list": obs_meta.obs_info.wafer_slots_list.split(","),
            }
        # Ensure obs_ids are sorted by their timestamp
        # Order the obs_ids based on their timestamp it is in the obs_meta.obs_info.timestamp

        self._splits = self._get_splits(ctx, obs_info)

    def _get_splits(self, ctx: Context, obs_info: Dict[str, str]) -> List[List[str]]:
        """
        Distribute the observations across splits based on the context and observation IDs.
        """
        raise NotImplementedError("This method should be implemented in subclasses to define how splits are created.")
