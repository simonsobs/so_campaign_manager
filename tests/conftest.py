import shutil
from collections import namedtuple
from pathlib import Path

import pytest

TomlReturn = namedtuple("TomlReturn", ["toml"])


@pytest.fixture
def simple_toml(tmp_path):
    d = tmp_path
    p = d / "campaign.toml"
    p.write_text(
        """
        [campaign.ml-mapmaking]
        context = "context.yaml"
        area = "so_geometry_v20250306_lat_f090.fits"
        output_dir = "output"
        bands = "f090"
        wafer = "ws0"
        comps = "TQU"
        maxiter = 10
        query = "obs_id='1575600533.1575611468.ar5_1'"
        tiled = 1
        site = "act"
        [campaign.ml-mapmaking.environment]
        MOBY2_TOD_STAGING_PATH = "/tmp/"
        DOT_MOBY2 = "act_dot_moby2"
        SOTODLIB_SITECONFIG = "site.yaml"
    """
    )
    return TomlReturn(p)


@pytest.fixture
def lite_toml(tmp_path):
    d = tmp_path
    p = d / "campaign.toml"
    p.write_text(
        """
        [campaign.ml-mapmaking]
        context = "context.yaml"
        area = "so_geometry_v20250306_lat_f090.fits"
        output_dir = "output"
        query = "obs_id='1575600533.1575611468.ar5_1'"
        site = "act"
        [campaign.ml-mapmaking.resources]
        ranks = 8
        threads = 1
    """
    )
    return TomlReturn(p)
