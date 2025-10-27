from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sotodlib.core import Context

from socm.utils.misc import get_query_from_file
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
        final_query = self.query
        if self.query.startswith("file://"):
            query_path = Path(self.query.split("file://")[-1]).absolute()
            final_query = get_query_from_file(query_path)
        obs_ids = ctx.obsdb.query(final_query)
        obs_info = dict()
        for obs_id in obs_ids:
            self.datasize += obs_id["n_samples"]
            obs_info[obs_id["obs_id"]] = {
                "start_time": obs_id["timestamp"],
                "wafer_list": obs_id["wafer_slots_list"].split(","),
                "tube_slot": obs_id.get("tube_slot", "st1"),
                "az_center": obs_id["az_center"],
                "el_center": obs_id["el_center"],
                "pwv": obs_id.get("pwv", 0),
            }
        # Ensure obs_ids are sorted by their timestamp
        # Order the obs_ids based on their timestamp it is in the obs_meta.obs_info.timestamp

        self._splits = self._get_splits(ctx, obs_info)

    def _get_num_chunks(self, num_obs: int) -> int:
        num_chunks = (
            num_obs + self.chunk_nobs - 1
        ) // self.chunk_nobs  # Ceiling division
        return num_chunks

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> List[List[str]]:
        """
        Distribute the observations across splits based on the context and observation IDs.
        """
        if self.__class__.__name__ != "NullTestWorkflow":
            raise NotImplementedError(
                "This method should be implemented in subclasses."
            )
        else:
            pass

    @classmethod
    def get_workflows(cls, desc: Dict[str, Any]) -> List["NullTestWorkflow"]:
        """
        Distribute the observations across splits based on the context and observation IDs.
        """
        if cls.__name__ != "NullTestWorkflow":
            raise NotImplementedError(
                "This method should be implemented in subclasses."
            )
        else:
            pass

    def get_arguments(self) -> List[str]:
        """
        Get the command to run the ML mapmaking workflow.
        """
        area = Path(self.area.split("file://")[-1])
        query = Path(self.query.split("file://")[-1])
        preprocess_config = Path(self.preprocess_config.split("file://")[-1])

        arguments = [f"{query.absolute()}", f"{area.absolute()}", self.output_dir, f"{preprocess_config.absolute()}"]
        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
            elif isinstance(v, list):
                v = ",".join([str(item) for item in v])
            if k not in [
                "area",
                "output_dir",
                "executable",
                "query",
                "id",
                "environment",
                "resources",
                "datasize",
                "chunk_nobs",
                "nsplits",
                "wafers",
                "subcommand",
                "name",
                "chunk_duration",
                "preprocess_config"
            ]:
                arguments.append(f"--{k}={v}")
        return arguments
