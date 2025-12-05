from ..core import QosPolicy, Resource


class PerlmutterResource(Resource):
    """
    PerlmutterResource is a specialized Resource class for the Perlmutter HPC system.
    It includes additional attributes specific to the Perlmutter system.
    """

    name: str = "perlmutter"
    nodes: int = 3072
    cores_per_node: int = 128
    memory_per_node: int = 1000000  # in MB
    default_qos: str = "regular"

    def __init__(self, **data):
        super().__init__(**data)
        self.qos = [QosPolicy(name="regular", max_walltime=2880, max_jobs=5000, max_cores=393216),
                    QosPolicy(name="interactive", max_walltime=240, max_jobs=2, max_cores=512),
                    QosPolicy(name="shared_interactive", max_walltime=240, max_jobs=2, max_cores=64),
                    QosPolicy(name="debug", max_walltime=30, max_jobs=5, max_cores=1024)
                    ]
