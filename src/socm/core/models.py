from typing import Callable, List, Optional, Tuple

from pydantic import BaseModel

# from sotodlid.core import Context


class Resource(BaseModel):
    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int
    default_queue: str = "normal"
    maximum_walltime: int = 1440


class Task(BaseModel):
    name: str
    performance: Optional[Callable] = None


class Workflow(BaseModel):
    id: int
    config: str
    ordered_tasks: List[Task]
    observations: List[str]
    context_file: str

    def get_num_cores_memory(self, resource: Resource) -> Tuple[int, int]:
        """
        Based on the observation list, and task memory requirements return the
        total memory of this workflow
        """
        import random

        # context = Context(self.context_file)

        # for observation in self.observations:
        #     obs = context.get_obs(observation)
        #     self.observations_length += obs.obs_info.duration

        # total_memory = 500 * self.observations_length

        # total_memory / resource.memory_per_node
        return random.randint(1, 16), 2000

    def get_expected_execution_time(self, resource: Resource) -> int:
        """
        Calculate the expected execution time based on the the number of nodes,
        task list and observation size
        """
        import random

        return random.random() * 1000


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    capaign_policy: str
    resource: str = "tiger"
