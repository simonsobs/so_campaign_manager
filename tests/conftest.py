from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def mock_filemd5():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.bookkeeper.bookkeeper.FileMD5") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self):
                pass

            def parse_file(self, path: Path, gzip_file: bool = False):
                return "efca7302276bceac49b8326a7b88f008"

        # Set the side effect to use our implementation
        mocked.side_effect = MockContextImpl
        yield mocked


@pytest.fixture
def mock_queryfile(tmp_path):
    """Create a fixture that returns a mock Context class."""
    query = "1\n2\n3\n"
    p = tmp_path / "query.txt"
    p.write_text(query)
    return p


@pytest.fixture
def mock_slurmise():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.bookkeeper.bookkeeper.Slurmise") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self, toml_path):
                self._toml_path = toml_path

            def raw_record(self, job_data):
                assert dict(job_data) == {
                    "job_name": "ml_mapmaking_workflow",
                    "slurm_id": "1181754.5",
                    "categorical": {
                        "subcommand": "make-ml-map",
                        "area": "efca7302276bceac49b8326a7b88f008",
                        "comps": "TQU",
                        "bands": "f090",
                        "nmat": "corr",
                        "site": "act",
                    },
                    "numerical": {
                        "ranks": 1,
                        "threads": 32,
                        "datasize": 259864,
                        "downsample": 1,
                        "maxiter": 10,
                        "tiled": 1,
                    },
                    "memory": 41669,
                    "runtime": 2.05,
                    "cmd": "srun --cpu_bind=cores --export=ALL --ntasks-per-node=1 --cpus-per-task=8 so-site-pipeline make-ml-map obs_id='1575600533.1575611468.ar5_1' /scratch/gpfs/SIMONSOBS/so/science-readiness/footprint/v20250306/so_geometry_v20250306_lat_f090.fits /scratch/gpfs/SIMONSOBS/users/ip8725/git/so_mapmaking_campaign_manager/output --bands=f090 --comps=TQU --context=/scratch/gpfs/ACT/data/context-so-fixed/context.yaml --maxiter=10 --site=act --tiled=1 --wafer=ws0",
                }

        # Set the side effect to use our implementation
        mocked.side_effect = MockContextImpl
        yield mocked


@pytest.fixture
def mock_parse_slurm_job_metadata():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.bookkeeper.bookkeeper.parse_slurm_job_metadata") as mocked:
        # Create the mock context behavior
        # Set the side effect to use our implementation
        mocked.return_value = {
            "slurm_id": 1181754,
            "step_id": "5",
            "job_name": "interactive",
            "state": "RUNNING",
            "partition": "cpu",
            "elapsed_seconds": 123,
            "CPUs": 112,
            "memory_per_cpu": {"set": True, "infinite": False, "number": 8000},
            "memory_per_node": {"set": False, "infinite": False, "number": 0},
            "max_rss": 41669,
        }

        yield mocked


@pytest.fixture
def mock_context():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.workflows.ml_mapmaking.Context") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self, context_file):
                self.obsdb = mock.Mock()
                self.obsdb.query = mock.Mock(
                    return_value=[
                        {"obs_id": "1575600533.1575611468.ar5_1", "n_samples": 259584}
                    ]
                )

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
            "deadline": "2d",
            "resources": {"nodes": 4, "cores-per-node": 112},
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
                "resources": {
                    "ranks": 8,
                    "threads": 8,
                    "memory": "80000",
                    "runtime": "80000",
                },
                "environment": {
                    "DOT_MOBY2": "act_dot_moby2",
                    "SOTODLIB_SITECONFIG": "site.yaml",
                },
            },
            "ml-null-tests.mission-tests": {
                "chunk_nobs": 5,
                "nsplits": 4,
                "resources": {
                    "ranks": 4,
                    "threads": 8,
                    "memory": "80000",
                    "runtime": "80000",
                },
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
                "environment": {
                    "DOT_MOBY2": "act_dot_moby2",
                    "SOTODLIB_SITECONFIG": "site.yaml",
                },
            },
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
            },
            "sat-sims": {
                "context": "context.yaml",
                "schedule": "schedule0002.txt",
                "output_dir": "output",
                "filterbin_name": "filterbin_01_schedule0002",
                "resources": {
                    "ranks": 8,
                    "threads": 1,
                },
            },
        }
    }

    return config


@pytest.fixture
def campaign_config():
    config = {
        "campaign": {
            "deadline": "2d",
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
                "resources": {
                    "ranks": 8,
                    "threads": 8,
                    "memory": "80000",
                    "runtime": "80000",
                },
            },
            "ml-null-tests": {
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
                "environment": {
                    "DOT_MOBY2": "act_dot_moby2",
                    "SOTODLIB_SITECONFIG": "site.yaml",
                },
                "mission-tests": {
                    "chunk_nobs": 5,
                    "nsplits": 4,
                    "resources": {
                        "ranks": 4,
                        "threads": 8,
                        "memory": "80000",
                        "runtime": "80000",
                    },
                },
                "wafer-tests": {
                    "chunk_nobs": 10,
                    "nsplits": 8,
                    "resources": {
                        "ranks": 1,
                        "threads": 32,
                        "memory": "80000",
                        "runtime": "80000",
                    },
                },
                "direction-tests": {
                    "chunk_nobs": 10,
                    "nsplits": 8,
                    "resources": {
                        "ranks": 1,
                        "threads": 32,
                        "memory": "80000",
                        "runtime": "80000",
                    },
                },
                "pwv-tests": {
                    "chunk_nobs": 10,
                    "nsplits": 8,
                    "resources": {
                        "ranks": 1,
                        "threads": 32,
                        "memory": "80000",
                        "runtime": "80000",
                    },
                },
            },
        },
    }
    return config
