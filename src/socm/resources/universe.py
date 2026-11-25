from ..core import QosPolicy, Resource


class UniverseResource(Resource):
    """
    Resource definition for the Universe HPC cluster at Princeton.

    Pre-configures the node count, core layout, memory, and SLURM QoS
    policies for the Universe cluster so that campaigns can reference it
    by name in ``registered_resources``.

    Attributes
    ----------
    name : str
        Resource identifier, fixed to ``"universe"``.
    nodes : int
        Total compute nodes available (28).
    cores_per_node : int
        CPU cores per node (224).
    memory_per_node : int
        Memory per node in MB (1 000 000).
    default_qos : str
        Default QoS name (``"main"``).

    QoS tiers
    ----------
    main
        30 d walltime, 5 000 jobs, 6 272 cores.
    """

    name: str = "universe"
    nodes: int = 28
    cores_per_node: int = 224
    memory_per_node: int = 1000000  # in MB
    default_qos: str = "main"

    def __init__(self, **data):
        super().__init__(**data)
        self.qos = [QosPolicy(name="main", max_walltime=43200, max_jobs=5000, max_cores=6272)]
