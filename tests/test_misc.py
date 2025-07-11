from socm.utils.misc import get_workflow_entries
from socm.workflows import subcampaign_map


def test_workflow_entries(campaign_config):
    workflows_configs = get_workflow_entries(campaign_config, subcampaign_map=subcampaign_map)

    assert workflows_configs == {
        "resources": {"nodes": 4, "cores-per-node": 112},
        "ml-mapmaking": {
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "resources": {"ranks": 8, "threads": 8, "memory": "80000", "runtime": "80000"},
        },
        "ml-null-tests.mission-tests": {
            "chunk_nobs": 5,
            "nsplits": 4,
            "resources": {"ranks": 4, "threads": 8, "memory": "80000", "runtime": "80000"},
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {"DOT_MOBY2": "act_dot_moby2", "SOTODLIB_SITECONFIG": "site.yaml"},
        },
        "ml-null-tests.wafer-tests": {
            "chunk_nobs": 10,
            "nsplits": 8,
            "resources": {"ranks": 1, "threads": 32, "memory": "80000", "runtime": "80000"},
            "context": "context.yaml",
            "area": "so_geometry_v20250306_lat_f090.fits",
            "output_dir": "output/null_tests",
            "bands": "f090",
            "wafer": "ws0",
            "comps": "TQU",
            "maxiter": 10,
            "query": "obs_id IN ('1551468569.1551475843.ar5_1')",
            "tiled": 1,
            "site": "act",
            "environment": {"DOT_MOBY2": "act_dot_moby2", "SOTODLIB_SITECONFIG": "site.yaml"},
        },
    }
