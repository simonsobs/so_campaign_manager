from pathlib import Path
from typing import Any, List, Optional, Union

from sotodlib.core import Context

from socm.core import Workflow
from socm.utils.misc import get_query_from_file


class MLMapmakingWorkflow(Workflow):
    """
    A workflow for ML mapmaking.
    """

    area: str
    output_dir: str
    query: str = "1"
    name: str = "ml_mapmaking_workflow"
    executable: str = "so-site-pipeline"
    subcommand: str = "make-ml-map"
    datasize: int = 0
    comps: Optional[str] = "TQU"
    wafers: Optional[str] = None
    bands: Optional[str] = None
    nmat: Optional[str] = "corr"
    max_dets: Optional[int] = None
    site: Optional[str] = "so_lat"
    downsample: Union[int, List[int]] = 1
    maxiter: Union[int, List[int]] = 500
    tiled: int = 1

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialization to set the context for the workflow.
        """
        ctx_file = Path(self.context.split("file://")[-1]).absolute()
        ctx = Context(ctx_file)

        final_query = self.query
        if self.query.startswith("file://"):
            self.query = Path(self.query.split("file://")[-1]).absolute()
            final_query = get_query_from_file(self.query)
        obs_ids = ctx.obsdb.query(final_query)
        for obs_id in obs_ids:
            self.datasize += obs_id["n_samples"]

    def get_command(self) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={self.resources['ranks']} --cpus-per-task={self.resources['threads']} {self.executable} {self.subcommand} "
        command += " ".join(self.get_arguments())

        return command.strip()

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
                "output_dir",
                "id",
                "environment",
                "resources",
                "datasize",
            ]:
                arguments.append(f"--{k}={v}")
        return arguments

    @classmethod
    def get_workflows(
        cls, descriptions: Union[List[dict], dict]
    ) -> List["MLMapmakingWorkflow"]:
        """
        Create a list of MLMapmakingWorkflow instances from the provided descriptions.
        """
        if isinstance(descriptions, dict):
            descriptions = [descriptions]

        workflows = []
        for desc in descriptions:
            workflow = cls(**desc)
            workflows.append(workflow)

        return workflows
