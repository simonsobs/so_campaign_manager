from datetime import timedelta

from socm.workflows.null_tests import NullTestWorkflow


class MissionNullTests(NullTestWorkflow):
    """
    A workflow for time null tests.
    """
    chunk_duration: timedelta = timedelta(days=1)
    nsplits: int = 8

    def get_command(self, ranks:int=1, query:str="1") -> str:
        """
        Get the command to run the time null test workflow.
        """
        command = f"--ntasks-per-node={ranks} python make_ml_mapmaker <query> "
        command += f"{self.area} {self.output_folder} "
        command += f"--executable {self.executable} "
        command += f"-C {self.context_file} "
        if self.config:
            config_str = " ".join(f"--{k} {v}" for k, v in self.config.items())
            command += f" {config_str}"
        return command
        return f"run_time_null_test --context {self.context} --area {self.area} --output-dir {self.output_dir} --maxiters {self.maxiters} --site {self.site} --query {self.query}"