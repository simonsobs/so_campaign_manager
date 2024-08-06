import json
import sqlite3
from typing import Callable, List, Optional, Tuple

import yaml
from pydantic import BaseModel
from sotodlib.core.util import tag_substr

from ..utils.const import PERFORMANCE_QUERY
from ..utils.misc import dict_factory


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
    name: str
    executable: str
    context_file: str
    subcommand: str
    config: str
    observations: Optional[List[str]] = []

    def get_num_cores_memory(self, resource: Resource) -> Tuple[int, int]:
        """
        Based on the observation list, and task memory requirements return the
        total memory of this workflow
        """
        with open(self.context_file, "r") as file:
            context = yaml.safe_load(file)
        with open(self.config, "r") as file:
            config = yaml.safe_load(file)

        context = tag_substr(dest=context, tags=context["tags"])
        obs_db_con = sqlite3.connect(context["obsdb"])
        obs_db_con.row_factory = dict_factory
        obs_db_cur = obs_db_con.cursor()
        obs_db_cur.execute(
            "select n_samples from obs where obs_id=:obs_id",
            {"obs_id": config["observation_id"]},
        )
        n_samples = obs_db_cur.fetchone()["n_samples"]
        obs_db_con.close()

        performance_db_con = sqlite3.connect("something")
        performance_db_con.row_factory = dict_factory
        performance_db_cur = performance_db_con.cursor()
        performance_db_cur.execute(
            PERFORMANCE_QUERY,
            {"workflow_name": self.executable, "subcommand": self.subcommand},
        )

        performance = performance_db_cur.fetchone()

        perf_fun = json.loads(performance["memory_function"])
        total_memory = perf_fun(n_samples, *performance["memory_params"])

        return 1, total_memory

    def get_expected_execution_time(self, resource: Resource) -> int:
        """
        Calculate the expected execution time based on the the number of nodes,
        task list and observation size
        """
        with open(self.context_file, "r") as file:
            context = yaml.safe_load(file)
        with open(self.config, "r") as file:
            config = yaml.safe_load(file)

        context = tag_substr(dest=context, tags=context["tags"])
        obs_db_con = sqlite3.connect(context["obsdb"])
        obs_db_con.row_factory = dict_factory
        obs_db_cur = obs_db_con.cursor()
        obs_db_cur.execute(
            "select n_samples from obs where obs_id=:obs_id",
            {"obs_id": config["observation_id"]},
        )
        n_samples = obs_db_cur.fetchone()["n_samples"]
        obs_db_con.close()

        performance_db_con = sqlite3.connect("something")
        performance_db_con.row_factory = dict_factory
        performance_db_cur = performance_db_con.cursor()
        performance_db_cur.execute(
            PERFORMANCE_QUERY,
            {"workflow_name": self.executable, "subcommand": self.subcommand},
        )

        performance = performance_db_cur.fetchone()

        perf_fun = json.loads(performance["time_function"])
        expected_execution = perf_fun(n_samples, *performance["time_params"])
        return expected_execution


class Campaign(BaseModel):
    id: int
    workflows: List[Workflow]
    campaign_policy: str
    resource: str = "tiger2"
