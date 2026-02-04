from ..core import QosPolicy, Resource


class TigerResource(Resource):
    """
    TigerResource is a specialized Resource class for the Tiger HPC system.
    It includes additional attributes specific to the Tiger system.
    """

    name: str = "tiger3"
    nodes: int = 492
    cores_per_node: int = 112
    memory_per_node: int = 1000000  # in MB
    default_qos: str = "test"

    def __init__(self, **data):
        super().__init__(**data)
        self.qos = [QosPolicy(name="test", max_walltime=60, max_jobs=1, max_cores=8000),
                    QosPolicy(name="vshort", max_walltime=300, max_jobs=2000, max_cores=55104),
                    QosPolicy(name="short", max_walltime=1440, max_jobs=50, max_cores=8000),
                    QosPolicy(name="medium", max_walltime=4320, max_jobs=80, max_cores=4000),
                    QosPolicy(name="long", max_walltime=8640, max_jobs=16, max_cores=1000),
                    QosPolicy(name="vlong", max_walltime=21600, max_jobs=8, max_cores=900)
                    ]
