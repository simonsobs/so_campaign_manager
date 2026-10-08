from socm.workflows.get_schedule import GetScheduleWorkflow
from socm.workflows.lat_simulation import LATSimWorkflow
from socm.workflows.sat_simulation import SATSimWorkflow
from socm.workflows.shell_script import ShellScriptWorkflow
from socm.workflows.spectra import SpectraWorkflow

registered_workflows = {
    "power-spectra": SpectraWorkflow,
    "get-schedule": GetScheduleWorkflow,
    "sat-sims": SATSimWorkflow,
    "lat-sims": LATSimWorkflow,
    "shell-script": ShellScriptWorkflow,
}

subcampaign_map = {}

try:
    from socm.workflows.ml_mapmaking import MLMapmakingWorkflow
    from socm.workflows.ml_null_tests import (
        DayNightNullTestWorkflow,
        DirectionNullTestWorkflow,
        ElevationNullTestWorkflow,
        MoonCloseFarNullTestWorkflow,
        MoonRiseSetNullTestWorkflow,
        PWVNullTestWorkflow,
        SmartSplitNullTestWorkflow,
        SunCloseFarNullTestWorkflow,
        TimeNullTestWorkflow,
        WaferNullTestWorkflow,
    )

    registered_workflows.update({
        "ml-mapmaking": MLMapmakingWorkflow,
        "ml-null-tests.mission-tests": TimeNullTestWorkflow,
        "ml-null-tests.wafer-tests": WaferNullTestWorkflow,
        "ml-null-tests.direction-tests": DirectionNullTestWorkflow,
        "ml-null-tests.pwv-tests": PWVNullTestWorkflow,
        "ml-null-tests.day-night-tests": DayNightNullTestWorkflow,
        "ml-null-tests.moonrise-set-tests": MoonRiseSetNullTestWorkflow,
        "ml-null-tests.elevation-tests": ElevationNullTestWorkflow,
        "ml-null-tests.sun-close-tests": SunCloseFarNullTestWorkflow,
        "ml-null-tests.moon-close-tests": MoonCloseFarNullTestWorkflow,
        "ml-null-tests.smart-split-tests": SmartSplitNullTestWorkflow,
    })

    subcampaign_map.update({
        "ml-null-tests": [
            "mission-tests",
            "wafer-tests",
            "direction-tests",
            "pwv-tests",
            "day-night-tests",
            "moonrise-set-tests",
            "elevation-tests",
            "sun-close-tests",
            "moon-close-tests",
            "smart-split-tests",
        ]
    })
except ImportError:
    pass
