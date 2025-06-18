
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

    def get_command(self, ranks: int = 1) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"srun --cpu_bind=cores --export=ALL --ntasks-per-node={ranks} --cpus-per-task=8 {self.executable} {self.subcommand} "
        command += self.get_arguments()

        return command.strip()

    def get_arguments(self) -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        arguments = f"{self.query} {self.area} {self.output_dir} "
        sorted_workflow = dict(sorted(self.model_dump(exclude_unset=True).items()))

        for k, v in sorted_workflow.items():
            if k not in [
                "area",
                "output_dir",
                "executable",
                "query",
                "output_dir",
                "id",
                "environment",
                "resources",
            ]:
                arguments += f"--{k}={v} "
        return arguments.strip()
