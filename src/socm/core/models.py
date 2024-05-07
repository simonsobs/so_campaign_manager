from typing import List, Optional

from pydantic import BaseModel
from sotodlid.core import Context


class Resource(BaseModel):
    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int


class PerformanceModel(BaseModel):
    resource: Resource
    model_parameters: List[float]


class Task(BaseModel):
    name: str
    performance: PerformanceModel


class Workflow(BaseModel):
    id: int
    config: str
    ordered_tasks: List[Task]
    experiment: str = "so" | "act"
    observations: List[str]
    context_file: str
    observations_length: Optional[int] = 0

    def get_observation_length(self):

        context = Context(self.context_file)

        for observation in self.observations:
            obs = context.get_obs(observation)
            self.observations_length += obs.obs_info.duration


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    resource: str = "tiger"
