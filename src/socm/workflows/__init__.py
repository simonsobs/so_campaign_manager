from socm.workflows.spectra import SpectraWorkflow  # noqa: F401

registered_workflows = {
    "power-spectra": SpectraWorkflow,
}

subcampaign_map = {}

try:
    from socm.workflows.ml_mapmaking import MLMapmakingWorkflow  # noqa: F401
    from socm.workflows.ml_null_tests import (  # noqa: F401
        DayNightNullTestWorkflow,
        DirectionNullTestWorkflow,
        ElevationNullTestWorkflow,
        MoonCloseFarNullTestWorkflow,
        MoonRiseSetNullTestWorkflow,
        PWVNullTestWorkflow,
        SunCloseFarNullTestWorkflow,
        TimeNullTestWorkflow,
        WaferNullTestWorkflow,
    )
    from socm.workflows.sat_simulation import SATSimWorkflow  # noqa: F401

    registered_workflows.update({
        "sat-sims": SATSimWorkflow,
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
        ]
    })
except ImportError:
    pass
