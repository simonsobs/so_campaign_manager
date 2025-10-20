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
        self._existing_jobs = {}

    def fits_in_qos(self, walltime: int, cores: int) -> QosPolicy | None:
        """
        Check if the given walltime and cores fit within the specified QoS policy.

        Args:
            walltime (int): The requested walltime in minutes.
            cores (int): The requested number of cores.

        Returns:
            QosPolicy | None: The name of the matching QoS policy object or None if no match is found.
        """

        # What happens when the job does not fit in the best possible QoS?
        for policy in self.qos:
            existing_jobs = self._existing_jobs.get(policy.name, [])
            remaining_cores = policy.max_cores - sum(job[2] for job in existing_jobs)
            if policy.max_walltime >= walltime and remaining_cores >= cores and len(existing_jobs) < policy.max_jobs:
                return policy
        return None

    def register_job(self, job_id: str, walltime: int, cores: int) -> bool:
        """
        Register a job with the resource if it fits within the QoS policies.

        Args:
            job_id (str): The unique identifier for the job.
            walltime (int): The requested walltime in minutes.
            cores (int): The requested number of cores.

        Returns:
            bool: True if the job was registered successfully, False otherwise.
        """
        qos_policy = self.fits_in_qos(walltime, cores)
        if qos_policy:
            qos_name = qos_policy.name
            existing_jobs = self._existing_jobs.get(qos_name, [])
            existing_jobs.append((job_id, walltime, cores))
            self._existing_jobs[qos_name] = existing_jobs
            return True
        return False
