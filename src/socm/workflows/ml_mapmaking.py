
from ..core.models import Workflow


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


    def get_command(self, ranks:int=1) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={ranks} --cpus-per-task=8 {self.executable} {self.subcommand} {self.query} "
        command += f"{self.area} {self.output_dir} "
        test = dict(sorted(self.model_dump(exclude_unset=True).items()))
        print(f"MLMapmakingWorkflow: {test}, type={type(test)}")
        for k, v in test.items():
            if k not in ["area", "output_dir", "executable", "query", "output_dir"]:
                command += f"--{k}={v} "
        return command.strip()