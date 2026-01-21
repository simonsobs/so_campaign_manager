import versioneer  # comes from the `some-build-toolkit` library
from setuptools import setup

setup(
    name="socm",
    version=versioneer.get_versions()["version"],
)
