from typing import List, Optional

from pydantic import BaseModel


class Resource(BaseModel):
    name: str
    nodes: int
    cores_per_node: int
    memory_per_node: int
    default_queue: str = "normal"
    maximum_walltime: int = 1440


class Workflow(BaseModel):
    name: str
    executable: str
    context: str
    subcommand: str
    id: Optional[int] = None

    model_config = {
        "extra": "allow",
    }

    def get_command(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")

    def get_arguments(self, **kargs) -> str:
        raise NotImplementedError("This method should be implemented in subclasses")


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    campaign_policy: str
    resource: str = "tiger3"
