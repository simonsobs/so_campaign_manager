from ..core import QosPolicy, Resource


class LocalResource(Resource):
    """
    LocalResource is a specialized Resource class for the localhost.
    """

    name: str = "localhost"
    nodes: int = 1
    cores_per_node: int = 8
    memory_per_node: int = 64000  # in MB
    default_qos: str = "default"

    def __init__(self, **data):
        super().__init__(**data)
        self.qos = [QosPolicy(name="default", max_walltime=6000, max_jobs=1, max_cores=8),
                    ]
