from ..core import QosPolicy, Resource


class TigerResource(Resource):
    """
    Resource definition for the Tiger 3 HPC cluster at Princeton.

    Pre-configures the node count, core layout, memory, and SLURM QoS
    policies for Tiger 3 so that campaigns can reference it by name
    (``"tiger3"`` in ``registered_resources``).

    The QoS tiers are configured in ascending order of walltime, from
    the most restrictive ``test`` tier to the most permissive ``vlong``
    tier. The planner iterates this list in order and selects the first
    tier that satisfies a job's walltime and core requirements.

    Attributes
    ----------
    name : str
        Resource identifier, fixed to ``"tiger3"``.
    nodes : int
        Total compute nodes available (492).
    cores_per_node : int
        CPU cores per node (112).
    memory_per_node : int
        Memory per node in MB (1 000 000).
    default_qos : str
        Default QoS name used when no specific policy is required (``"test"``).

    QoS tiers
    ----------
    test
        1 h walltime, 1 job, 8 000 cores.
    vshort
        5 h walltime, 2 000 jobs, 55 104 cores.
    short
        24 h walltime, 50 jobs, 8 000 cores.
    medium
        3 d walltime, 80 jobs, 4 000 cores.
    long
        6 d walltime, 16 jobs, 1 000 cores.
    vlong
        15 d walltime, 8 jobs, 900 cores.
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
