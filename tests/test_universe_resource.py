from socm.core.models import QosPolicy
from socm.resources.universe import UniverseResource


def test_universe_resource_init():
    """Test UniverseResource creation with default values."""
    resource = UniverseResource()

    # Verify default attributes
    assert resource.name == "universe"
    assert resource.nodes == 28
    assert resource.cores_per_node == 224
    assert resource.memory_per_node == 1000000
    assert resource.default_qos == "main"

    # Should have 1 QoS policy
    assert len(resource.qos) == 1

    # Verify each policy exists with correct parameters
    qos_dict = {policy.name: policy for policy in resource.qos}
    assert list(qos_dict.keys()) == ["main"]
    assert qos_dict["main"].max_walltime == 43200
    assert qos_dict["main"].max_jobs == 5000
    assert qos_dict["main"].max_cores == 6272
    assert hasattr(resource, "_existing_jobs")
    assert isinstance(resource._existing_jobs, dict)
    assert len(resource._existing_jobs) == 0


def test_universe_resource_custom_values():
    """Test UniverseResource with custom values overriding defaults."""
    resource = UniverseResource(
        name="universe_custom",
        nodes=100,
        cores_per_node=64,
        memory_per_node=50000
    )

    assert resource.name == "universe_custom"
    assert resource.nodes == 100
    assert resource.cores_per_node == 64
    assert resource.memory_per_node == 50000
    # QoS policies should still be initialized
    assert len(resource.qos) == 1


def test_fits_in_qos_perfect_fit():
    """Test that a job fits perfectly in one QoS."""
    resource = UniverseResource()

    qos = resource.fits_in_qos(walltime=20, cores=500)

    assert qos is not None
    assert isinstance(qos, QosPolicy)
    assert qos.name == "main"


def test_fits_in_qos_smallest_sufficient_policy():
    """Test that fits_in_qos returns the first (smallest) QoS that fits."""
    resource = UniverseResource()

    # Job that fits in the main QoS
    qos = resource.fits_in_qos(walltime=100, cores=1000)

    assert qos is not None
    assert qos.name == "main"  # First match


def test_fits_in_qos_walltime_too_long():
    """Test that a job with walltime exceeding all QoS limits returns None."""
    resource = UniverseResource()
    # Walltime exceeds main QoS limit (43200 minutes)
    qos = resource.fits_in_qos(walltime=50000, cores=100)

    assert qos is None


def test_fits_in_qos_cores_too_many():
    """Test that a job requesting too many cores returns None."""
    resource = UniverseResource()
    # Cores exceed all QoS limits (max is 6272 in main)
    qos = resource.fits_in_qos(walltime=100, cores=7000)

    assert qos is None


def test_fits_in_qos_with_existing_jobs():
    """Test that fits_in_qos accounts for cores used by existing jobs."""
    resource = UniverseResource()
    # Fill main QoS almost completely (max is 6272)
    resource._existing_jobs = {"main": [("job1", 100, 6000)]}

    # Job should still fit in main since 6000 + 200 < 6272
    qos = resource.fits_in_qos(walltime=20, cores=200)
    assert qos == QosPolicy(name='main', max_walltime=43200, max_jobs=5000, max_cores=6272)

    # Now try with 300 cores (6000 + 300 = 6300 > 6272, exceeds main limit)
    # Should return None since no other QoS exists
    qos = resource.fits_in_qos(walltime=20, cores=300)
    assert qos is None


def test_fits_in_qos_no_remaining_cores():
    """Test when all cores in a QoS are consumed."""
    resource = UniverseResource()

    resource._existing_jobs = {"main": [("job1", 20, 6272)]}

    # Try to fit another job - should fail since main is full
    qos = resource.fits_in_qos(walltime=20, cores=100)
    assert qos is None


def test_register_job_success():
    """Test successfully registering a job that fits."""
    resource = UniverseResource()

    result = resource.register_job("job1", walltime=20, cores=500)

    assert result is True
    assert "main" in resource._existing_jobs
    assert len(resource._existing_jobs["main"]) == 1
    assert resource._existing_jobs["main"][0] == ("job1", 20, 500)


def test_register_job_failure_no_fit():
    """Test that registering a job that doesn't fit returns False."""
    resource = UniverseResource()

    # Job that doesn't fit in any QoS (walltime too long)
    result = resource.register_job("job1", walltime=50000, cores=1000)

    assert result is False
    assert len(resource._existing_jobs) == 0


def test_register_job_multiple_jobs_same_qos():
    """Test registering multiple jobs in the same QoS."""
    resource = UniverseResource()

    result1 = resource.register_job("job1", walltime=20, cores=500)
    result2 = resource.register_job("job2", walltime=25, cores=400)

    assert result1 is True
    assert result2 is True
    assert len(resource._existing_jobs["main"]) == 2
    assert resource._existing_jobs["main"][0] == ("job1", 20, 500)
    assert resource._existing_jobs["main"][1] == ("job2", 25, 400)


def test_register_job_fills_qos_exactly():
    """Test registering jobs until a QoS is completely full."""
    resource = UniverseResource()

    # Fill main QoS by registering multiple jobs
    result1 = resource.register_job("job1", walltime=100, cores=3000)
    result2 = resource.register_job("job2", walltime=100, cores=3272)

    assert result1 is True
    assert result2 is True

    # Verify main QoS is full
    main_jobs = resource._existing_jobs["main"]
    total_cores = sum(job[2] for job in main_jobs)
    assert total_cores == 6272

    # Next job should fail since there's no other QoS
    result3 = resource.register_job("job3", walltime=20, cores=100)
    assert result3 is False


def test_register_job_integration():
    """Test complete workflow: check fit, register job, verify remaining capacity."""
    resource = UniverseResource()

    # Check if job fits
    qos_before = resource.fits_in_qos(walltime=20, cores=1024)
    assert qos_before is not None
    assert qos_before == QosPolicy(name="main", max_walltime=43200, max_jobs=5000, max_cores=6272)

    # Register the job
    result = resource.register_job("large_job", walltime=20, cores=1024)
    assert result is True

    # Verify job was registered in main QoS
    qos_after = resource.fits_in_qos(walltime=20, cores=100)
    assert qos_after is not None
    assert qos_after == QosPolicy(name="main", max_walltime=43200, max_jobs=5000, max_cores=6272)
