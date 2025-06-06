
from ..core.models import Workflow


class MLMapmakingWorkflow(Workflow):
    """
    A workflow for ML mapmaking.
    """
    area: str
    output_dir: str
    query: str = "1"
    name: str = "ml_mapmaking_workflow_test"
    executable: str = "so-site-pipeline"
    subcommand: str = "make-ml-map"


    def get_command(self, ranks:int=1) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"--ntasks-per-node={ranks} python make_ml_mapmaker {self.query} "
        command += f"{self.area} {self.output_dir} "
        command += f"--executable {self.executable} "
        command += f"-C {self.context} "
        for k, v in self.model_dump(exclude_unset=True).items():
            if k not in ["area", "output_dir", "executable", "context"]:
                command += f"--{k} {v} "
        return command