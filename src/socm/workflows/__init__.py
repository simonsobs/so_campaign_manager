from socm.workflows.ml_mapmaking import MLMapmakingWorkflow  # noqa: F401
from socm.workflows.ml_null_tests import (  # noqa: F401
    TimeNullTestWorkflow,
    WaferNullTestWorkflow,
)
from socm.workflows.sat_simulation import SATSimWorkflow  # noqa: F401

registered_workflows = {
    "ml-mapmaking": MLMapmakingWorkflow,
    "sat-sims": SATSimWorkflow,
    "ml-null-tests.mission-tests": TimeNullTestWorkflow,
    "ml-null-tests.wafer-tests": WaferNullTestWorkflow,
}

subcampaign_map = {"ml-null-tests": ["mission-tests", "wafer-tests"]}
