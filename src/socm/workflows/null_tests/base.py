from socm.core.models import Workflow


class NullTestWorkflow(Workflow):
    """
    A workflow for null tests.
    """
    area: str
    output_dir: str
    maxiters: int
    site: str
    query: str

    def get_command(self, **kargs) -> str:
        """
        Get the command to run the null test workflow.
        """
        raise NotImplementedError("NullTestWorkflow does not implement get_command method.")