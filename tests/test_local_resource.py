from socm.resources import registered_resources
from socm.resources.localhost import LocalResource


def test_local_resource_defaults():
    resource = LocalResource()

    assert resource.name == "localhost"
    assert resource.nodes == 1
    assert resource.cores_per_node == 8
    assert resource.memory_per_node == 64000
    assert resource.default_qos == "default"

    assert len(resource.qos) == 1
    qos = resource.qos[0]
    assert qos.name == "default"
    assert qos.max_walltime == 6000
    assert qos.max_jobs == 1
    assert qos.max_cores == 8


def test_local_resource_is_registered():
    assert registered_resources["localhost"] is LocalResource


def test_local_resource_overrides():
    resource = LocalResource(cores_per_node=4, memory_per_node=16000)

    assert resource.cores_per_node == 4
    assert resource.memory_per_node == 16000


def test_local_resource_fits_in_qos():
    resource = LocalResource()

    assert resource.fits_in_qos(walltime=60, cores=8).name == "default"
    assert resource.fits_in_qos(walltime=60, cores=9) is None
    assert resource.fits_in_qos(walltime=6001, cores=1) is None
