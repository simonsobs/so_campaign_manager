from .ml_mapmaking import MLMapmakingWorkflow  # noqa: F401
from .sat_simulation import SATSimWorkflow  # noqa: F401

registered_workflows = {
    "ml-mapmaking": MLMapmakingWorkflow,
    "sat-sims": SATSimWorkflow,
}
