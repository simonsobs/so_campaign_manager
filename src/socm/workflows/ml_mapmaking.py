
from ..core.models import Workflow


class MLMapmakingWorkflow(Workflow):
    """
    A workflow for ML mapmaking.
    """
    area: str
    output_folder: str


    def get_command(self, ranks:int=1, query:str="1") -> str:
        """
        Get the command to run the ML mapmaking workflow.
        """
        command = f"--ntasks-per-node={ranks} python make_ml_mapmaker {query} "
        command += f"{self.area} {self.output_folder} "
        command += f"--executable {self.executable} "
        command += f"-C {self.context_file} "
        if self.config:
            config_str = " ".join(f"--{k} {v}" for k, v in self.config.items())
            command += f" {config_str}"
        return command