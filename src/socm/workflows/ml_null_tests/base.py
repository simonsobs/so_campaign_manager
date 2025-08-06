from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sotodlib.core import Context
from sotodlib.core.metadata.loader import LoaderError

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
        obs_ids = ctx.obsdb.query(self.query)
        obs_info = dict()
        for obs_id in obs_ids:
            self.datasize += obs_id["n_samples"]
            obs_info[obs_id["obs_id"]] = {
                "start_time": obs_id["timestamp"],
                "wafer_list": obs_id["wafer_slots_list"].split(","),
                "tube_slot": obs_id.get("tube_slot", "st1"),
                "az_center": obs_id["az_center"],
                "el_center": obs_id["el_center"],
                "pwv": obs_id["pwv"],
            }
        # Ensure obs_ids are sorted by their timestamp
        # Order the obs_ids based on their timestamp it is in the obs_meta.obs_info.timestamp

        self._splits = self._get_splits(ctx, obs_info)

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
        Create a list of NullTestWorkflows instances from the provided descriptions.
        """
        workflows = []
        try:
            for split in desc["_splits"]:
                desc_copy = desc.copy()
                desc_copy["query"] = "obs_id IN ("
                for oid in split:
                    desc_copy["query"] += f"'{oid}',"
                desc_copy["query"] = desc_copy["query"].rstrip(",")
                desc_copy["query"] += ")"
                desc_copy["chunk_nobs"] = 1
                desc_copy["output_dir"] = (
                    f"{desc['output_dir']}/mission_split_{len(workflows) + 1}"
                )
                workflow = cls(**desc_copy)
                workflows.append(workflow)
        except LoaderError as e:
            print(f"Error loading context: {e}")
            raise

        return workflows

    def get_arguments(self) -> List[str]:
        """
        Get the command to run the ML mapmaking workflow.
        """
        area = Path(self.area.split("file://")[-1])
        arguments = [self.query, f"{area.absolute()}", self.output_dir]
        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if isinstance(v, str) and v.startswith("file://"):
                v = Path(v.split("file://")[-1]).absolute()
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
            ]:
                arguments.append(f"--{k}={v}")
        return arguments
