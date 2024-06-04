from setuptools import setup
import versioneer  # comes from the `some-build-toolkit` library


setup(
    name="socm",
    version=versioneer.get_versions()["version"],
)
