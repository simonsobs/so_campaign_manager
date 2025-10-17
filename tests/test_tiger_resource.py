from socm.core.models import QosPolicy
from socm.resources.tiger import TigerResource


def test_tiger_resource_init():
    """Test TigerResource creation with default values."""
    resource = TigerResource()

    # Verify default attributes
    assert resource.name == "tiger3"
    assert resource.nodes == 492
    assert resource.cores_per_node == 112
    assert resource.memory_per_node == 1000000
    assert resource.default_qos == "test"

    # Should have 6 QoS policies
    assert len(resource.qos) == 6

    # Verify each policy exists with correct parameters
    qos_dict = {policy.name: policy for policy in resource.qos}
    assert list(qos_dict.keys()) == ["test", "vshort", "short", "medium", "long", "vlong"]

    assert qos_dict["test"].max_walltime == 60
    assert qos_dict["test"].max_jobs == 1
    assert qos_dict["test"].max_cores == 8000
    assert qos_dict["vshort"].max_walltime == 300
    assert qos_dict["vshort"].max_jobs == 2000
    assert qos_dict["vshort"].max_cores == 55104
    assert qos_dict["short"].max_walltime == 1440
    assert qos_dict["short"].max_jobs == 50
    assert qos_dict["short"].max_cores == 8000
    assert qos_dict["medium"].max_walltime == 4320
    assert qos_dict["medium"].max_jobs == 80
    assert qos_dict["medium"].max_cores == 4000
    assert qos_dict["long"].max_walltime == 8640
    assert qos_dict["long"].max_jobs == 16
    assert qos_dict["long"].max_cores == 1000
    assert qos_dict["vlong"].max_walltime == 21600
    assert qos_dict["vlong"].max_jobs == 8
    assert qos_dict["vlong"].max_cores == 900
    assert hasattr(resource, "_existing_jobs")
    assert isinstance(resource._existing_jobs, dict)
    assert len(resource._existing_jobs) == 0


def test_tiger_resource_custom_values():
    """Test TigerResource with custom values overriding defaults."""
    resource = TigerResource(
        name="tiger_custom",
        nodes=100,
        cores_per_node=64,
        memory_per_node=50000
    )

    assert resource.name == "tiger_custom"
    assert resource.nodes == 100
    assert resource.cores_per_node == 64
    assert resource.memory_per_node == 50000
    # QoS policies should still be initialized
    assert len(resource.qos) == 6


def test_fits_in_qos_perfect_fit():
    """Test that a job fits perfectly in one QoS."""
    resource = TigerResource()

    qos = resource.fits_in_qos(walltime=30, cores=4000)

    assert qos is not None
    assert isinstance(qos, QosPolicy)
    assert qos.name == "test"


def test_fits_in_qos_smallest_sufficient_policy():
    """Test that fits_in_qos returns the first (smallest) QoS that fits."""
    resource = TigerResource()

    # Job that could fit in multiple QoS policies
    # Should return 'test' (first one that fits)
    qos = resource.fits_in_qos(walltime=30, cores=1000)

    assert qos is not None
    assert qos.name == "test"  # First match


def test_fits_in_qos_walltime_too_long():
    """Test that a job with walltime exceeding all QoS limits returns None."""
    resource = TigerResource()

    # Walltime exceeds even vlong (21600 minutes)
    qos = resource.fits_in_qos(walltime=30000, cores=100)

    assert qos is None


def test_fits_in_qos_cores_too_many():
    """Test that a job requesting too many cores returns None."""
    resource = TigerResource()

    # Cores exceed all QoS limits (max is 55104 in vshort)
    qos = resource.fits_in_qos(walltime=100, cores=60000)

    assert qos is None


def test_fits_in_qos_with_existing_jobs():
    """Test that fits_in_qos accounts for cores used by existing jobs."""
    resource = TigerResource()
    resource._existing_jobs = {"test": [("job1", 30, 7000)]}

    qos = resource.fits_in_qos(walltime=30, cores=500)
    assert qos == QosPolicy(name="test", max_walltime=60, max_jobs=1, max_cores=8000)

    # Now try with 1500 cores (7000 + 1500 > 8000)
    qos = resource.fits_in_qos(walltime=30, cores=1500)
    assert qos == QosPolicy(name="vshort", max_walltime=300, max_jobs=2000, max_cores=55104)


def test_fits_in_qos_no_remaining_cores():
    """Test when all cores in a QoS are consumed."""
    resource = TigerResource()

    resource._existing_jobs = {"test": [("job1", 30, 8000)]}

    # Try to fit another job
    qos = resource.fits_in_qos(walltime=30, cores=100)
    assert qos == QosPolicy(name="vshort", max_walltime=300, max_jobs=2000, max_cores=55104)


def test_register_job_success():
    """Test successfully registering a job that fits."""
    resource = TigerResource()

    result = resource.register_job("job1", walltime=30, cores=1000)

    assert result is True
    assert "test" in resource._existing_jobs
    assert len(resource._existing_jobs["test"]) == 1
    assert resource._existing_jobs["test"][0] == ("job1", 30, 1000)


def test_register_job_failure_no_fit():
    """Test that registering a job that doesn't fit returns False."""
    resource = TigerResource()

    # Job that doesn't fit in any QoS (walltime too long)
    result = resource.register_job("job1", walltime=30000, cores=1000)

    assert result is False
    assert len(resource._existing_jobs) == 0


def test_register_job_multiple_jobs_same_qos():
    """Test registering multiple jobs in the same QoS."""
    resource = TigerResource()

    result1 = resource.register_job("job1", walltime=30, cores=2000)
    result2 = resource.register_job("job2", walltime=40, cores=3000)

    assert result1 is True
    assert result2 is True
    assert len(resource._existing_jobs["test"]) == 2
    assert resource._existing_jobs["test"][0] == ("job1", 30, 2000)
    assert resource._existing_jobs["test"][1] == ("job2", 40, 3000)


def test_register_job_multiple_jobs_different_qos():
    """Test registering jobs across different QoS policies."""
    resource = TigerResource()

    result1 = resource.register_job("job1", walltime=30, cores=8000)
    result2 = resource.register_job("job2", walltime=200, cores=5000)

    assert result1 is True
    assert result2 is True
    assert "test" in resource._existing_jobs
    assert "vshort" in resource._existing_jobs
    assert resource._existing_jobs["test"] == [("job1", 30, 8000)]
    assert resource._existing_jobs["vshort"] ==  [("job2", 200, 5000)]


def test_register_job_fills_qos_exactly():
    """Test registering jobs until a QoS is completely full."""
    resource = TigerResource()

    # Fill test QoS exactly (8000 cores)
    result1 = resource.register_job("job1", walltime=30, cores=5000)
    result2 = resource.register_job("job2", walltime=30, cores=3000)

    assert result1 is True
    assert result2 is True

    # Verify test QoS is full
    test_jobs = resource._existing_jobs["test"]
    total_cores = sum(job[2] for job in test_jobs)
    assert total_cores == 8000

    # Next job should go to vshort
    result3 = resource.register_job("job3", walltime=30, cores=100)
    assert result3 is True
    assert "vshort" in resource._existing_jobs


def test_register_job_integration():
    """Test complete workflow: check fit, register job, verify no more room."""
    resource = TigerResource()

    # Check if job fits
    qos_before = resource.fits_in_qos(walltime=30, cores=8000)
    assert qos_before is not None
    assert qos_before == QosPolicy(name="test", max_walltime=60, max_jobs=1, max_cores=8000)

    # Register the job
    result = resource.register_job("large_job", walltime=30, cores=8000)
    assert result is True

    # Verify test QoS is now full for small jobs
    qos_after = resource.fits_in_qos(walltime=30, cores=100)
    # Should skip test and return vshort
    assert qos_after is not None
    assert qos_after == QosPolicy(name="vshort", max_walltime=300, max_jobs=2000, max_cores=55104)
