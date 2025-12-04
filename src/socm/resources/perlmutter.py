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
