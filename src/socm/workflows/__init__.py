from socm.workflows.ml_mapmaking import MLMapmakingWorkflow  # noqa: F401
from socm.workflows.ml_null_tests import (  # noqa: F401
    DirectionNullTestWorkflow,
    PWVNullTestWorkflow,
    TimeNullTestWorkflow,
    WaferNullTestWorkflow,
)
from socm.workflows.sat_simulation import SATSimWorkflow  # noqa: F401

registered_workflows = {
    "ml-mapmaking": MLMapmakingWorkflow,
    "sat-sims": SATSimWorkflow,
    "ml-null-tests.mission-tests": TimeNullTestWorkflow,
    "ml-null-tests.wafer-tests": WaferNullTestWorkflow,
    "ml-null-tests.direction-tests": DirectionNullTestWorkflow,
    "ml-null-tests.pwv-tests": PWVNullTestWorkflow,
}

subcampaign_map = {
    "ml-null-tests": ["mission-tests", "wafer-tests", "direction-tests", "pwv-tests"]
}
