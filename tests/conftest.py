from unittest import mock

import pytest


@pytest.fixture
def mock_context():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.workflows.ml_mapmaking.Context") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self, context_file):
                self.obsdb = mock.Mock()
                self.obsdb.query = mock.Mock(return_value={"obs_id": ["1575600533.1575611468.ar5_1"]})

            def get_meta(self, obs_id):
                return mock.Mock(samps=mock.Mock(count=1000))

        # Set the side effect to use our implementation
        mocked.side_effect = MockContextImpl
        yield mocked


@pytest.fixture
def simple_config():
    """Return a dictionary with test configuration instead of a TOML file path."""
    config = {
        "campaign": {
            "ml-mapmaking": {
                "context": "context.yaml",
                "area": "so_geometry_v20250306_lat_f090.fits",
                "output_dir": "output",
                "bands": "f090",
                "wafer": "ws0",
                "comps": "TQU",
                "maxiter": 10,
                "query": "obs_id='1575600533.1575611468.ar5_1'",
                "tiled": 1,
                "site": "act",
                "environment": {
                    "MOBY2_TOD_STAGING_PATH": "/tmp/",
                    "DOT_MOBY2": "act_dot_moby2",
                    "SOTODLIB_SITECONFIG": "site.yaml",
                },
            }
        }
    }
    return config


@pytest.fixture
def lite_config():
    """
    A lightweight configuration for testing ML mapmaking workflows.
    """
    config = {
        "campaign": {
            "ml-mapmaking": {
                "context": "context.yaml",
                "area": "so_geometry_v20250306_lat_f090.fits",
                "output_dir": "output",
                "query": "obs_id='1575600533.1575611468.ar5_1'",
                "site": "act",
                "resources": {
                    "ranks": 8,
                    "threads": 1,
                },
            }
        }
    }

    return config
