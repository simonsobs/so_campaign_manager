from ..core import QosPolicy, Resource


class UniverseResource(Resource):
    """
    UniverseResource is a specialized Resource class for the Universe HPC system.
    It includes additional attributes specific to the Universe system.
    """

    name: str = "universe"
    nodes: int = 28
    cores_per_node: int = 224
    memory_per_node: int = 1000000  # in MB
    default_qos: str = "main"

    def __init__(self, **data):
        super().__init__(**data)
        self.qos = [QosPolicy(name="main", max_walltime=43200, max_jobs=5000, max_cores=6272)]
