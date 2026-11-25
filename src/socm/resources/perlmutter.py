from ..core import QosPolicy, Resource


class PerlmutterResource(Resource):
    """
    Resource definition for the Perlmutter HPC system at NERSC.

    Pre-configures the node count, core layout, memory, and SLURM QoS
    policies for Perlmutter so that campaigns can reference it by name
    in ``registered_resources``.

    Attributes
    ----------
    name : str
        Resource identifier, fixed to ``"perlmutter"``.
    nodes : int
        Total compute nodes available (3 072).
    cores_per_node : int
        CPU cores per node (128).
    memory_per_node : int
        Memory per node in MB (1 000 000).
    default_qos : str
        Default QoS name (``"regular"``).

    QoS tiers
    ----------
    regular
        48 h walltime, 5 000 jobs, 393 216 cores.
    interactive
        4 h walltime, 2 jobs, 512 cores.
    shared_interactive
        4 h walltime, 2 jobs, 64 cores.
    debug
        30 min walltime, 5 jobs, 1 024 cores.
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
