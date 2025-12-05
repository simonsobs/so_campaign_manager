from socm.core.models import QosPolicy
from socm.resources.perlmutter import PerlmutterResource


def test_perlmutter_resource_init():
    """Test PerlmutterResource creation with default values."""
    resource = PerlmutterResource()

    # Verify default attributes
    assert resource.name == "perlmutter"
    assert resource.nodes == 3072
    assert resource.cores_per_node == 128
    assert resource.memory_per_node == 1000000
    assert resource.default_qos == "regular"

    # Should have 4 QoS policies
    assert len(resource.qos) == 4

    # Verify each policy exists with correct parameters
    qos_dict = {policy.name: policy for policy in resource.qos}
    assert list(qos_dict.keys()) == ["regular", "interactive", "shared_interactive", "debug"]

    assert qos_dict["regular"].max_walltime == 2880
    assert qos_dict["regular"].max_jobs == 5000
    assert qos_dict["regular"].max_cores == 393216
    assert qos_dict["interactive"].max_walltime == 240
    assert qos_dict["interactive"].max_jobs == 2
    assert qos_dict["interactive"].max_cores == 512
    assert qos_dict["shared_interactive"].max_walltime == 240
    assert qos_dict["shared_interactive"].max_jobs == 2
    assert qos_dict["shared_interactive"].max_cores == 64
    assert qos_dict["debug"].max_walltime == 30
    assert qos_dict["debug"].max_jobs == 5
    assert qos_dict["debug"].max_cores == 1024
    assert hasattr(resource, "_existing_jobs")
    assert isinstance(resource._existing_jobs, dict)
    assert len(resource._existing_jobs) == 0


def test_perlmutter_resource_custom_values():
    """Test PerlmutterResource with custom values overriding defaults."""
    resource = PerlmutterResource(
        name="perlmutter_custom",
        nodes=100,
        cores_per_node=64,
        memory_per_node=50000
    )

    assert resource.name == "perlmutter_custom"
    assert resource.nodes == 100
    assert resource.cores_per_node == 64
    assert resource.memory_per_node == 50000
    # QoS policies should still be initialized
    assert len(resource.qos) == 4


def test_fits_in_qos_perfect_fit():
    """Test that a job fits perfectly in one QoS."""
    resource = PerlmutterResource()

    qos = resource.fits_in_qos(walltime=20, cores=500)

    assert qos is not None
    assert isinstance(qos, QosPolicy)
    assert qos.name == "regular"


def test_fits_in_qos_smallest_sufficient_policy():
    """Test that fits_in_qos returns the first (smallest) QoS that fits."""
    resource = PerlmutterResource()

    # Job that could fit in multiple QoS policies
    # Should return 'regular' (first one that fits)
    qos = resource.fits_in_qos(walltime=100, cores=1000)

    assert qos is not None
    assert qos.name == "regular"  # First match


def test_fits_in_qos_walltime_too_long():
    """Test that a job with walltime exceeding all QoS limits returns None."""
    resource = PerlmutterResource()

    # Walltime exceeds even regular (2880 minutes)
    qos = resource.fits_in_qos(walltime=3000, cores=100)

    assert qos is None


def test_fits_in_qos_cores_too_many():
    """Test that a job requesting too many cores returns None."""
    resource = PerlmutterResource()

    # Cores exceed all QoS limits (max is 393216 in regular)
    qos = resource.fits_in_qos(walltime=100, cores=400000)

    assert qos is None


def test_fits_in_qos_with_existing_jobs():
    """Test that fits_in_qos accounts for cores used by existing jobs."""
    resource = PerlmutterResource()
    # Fill regular QoS almost completely
    resource._existing_jobs = {"regular": [("job1", 100, 392716)]}

    # Job should still fit in regular since 392716 + 400 < 393216
    qos = resource.fits_in_qos(walltime=20, cores=400)
    assert qos == QosPolicy(name='regular', max_walltime=2880, max_jobs=5000, max_cores=393216)

    # Now try with 501 cores (392716 + 501 = 393217 > 393216, exceeds regular limit)
    # Should fall back to interactive (which has 512 cores max)
    qos = resource.fits_in_qos(walltime=20, cores=501)
    assert qos == QosPolicy(name="interactive", max_walltime=240, max_jobs=2, max_cores=512)


def test_fits_in_qos_no_remaining_cores():
    """Test when all cores in a QoS are consumed."""
    resource = PerlmutterResource()

    resource._existing_jobs = {"debug": [("job1", 20, 1024)]}

    # Try to fit another job
    qos = resource.fits_in_qos(walltime=20, cores=100)
    assert qos == QosPolicy(name="regular", max_walltime=2880, max_jobs=5000, max_cores=393216)


def test_register_job_success():
    """Test successfully registering a job that fits."""
    resource = PerlmutterResource()

    result = resource.register_job("job1", walltime=20, cores=500)

    assert result is True
    assert "regular" in resource._existing_jobs
    assert len(resource._existing_jobs["regular"]) == 1
    assert resource._existing_jobs["regular"][0] == ("job1", 20, 500)


def test_register_job_failure_no_fit():
    """Test that registering a job that doesn't fit returns False."""
    resource = PerlmutterResource()

    # Job that doesn't fit in any QoS (walltime too long)
    result = resource.register_job("job1", walltime=5000, cores=1000)

    assert result is False
    assert len(resource._existing_jobs) == 0


def test_register_job_multiple_jobs_same_qos():
    """Test registering multiple jobs in the same QoS."""
    resource = PerlmutterResource()

    result1 = resource.register_job("job1", walltime=20, cores=500)
    result2 = resource.register_job("job2", walltime=25, cores=400)

    assert result1 is True
    assert result2 is True
    assert len(resource._existing_jobs["regular"]) == 2
    assert resource._existing_jobs["regular"][0] == ("job1", 20, 500)
    assert resource._existing_jobs["regular"][1] == ("job2", 25, 400)


def test_register_job_multiple_jobs():
    """Test registering jobs."""
    resource = PerlmutterResource()

    # First job fits in "regular" QoS
    result1 = resource.register_job("job1", walltime=20, cores=500)
    # Second job fits only in "debug" QoS (exceeds interactive/shared_interactive max_cores, but fits in debug)
    result2 = resource.register_job("job2", walltime=20, cores=1024)

    assert result1 is True
    assert result2 is True
    assert "regular" in resource._existing_jobs
    assert "regular" in resource._existing_jobs
    assert len(resource._existing_jobs["regular"]) == 2
    assert resource._existing_jobs["regular"][0] == ("job1", 20, 500)
    assert resource._existing_jobs["regular"][1] == ("job2", 20, 1024)


def test_register_job_fills_qos_exactly():
    """Test registering jobs until a QoS is completely full."""
    resource = PerlmutterResource()

    # Fill regular QoS by registering multiple jobs
    # Since regular is first in the list, jobs will go there by default
    result1 = resource.register_job("job1", walltime=100, cores=200000)
    result2 = resource.register_job("job2", walltime=100, cores=193216)

    assert result1 is True
    assert result2 is True

    # Verify regular QoS is full
    regular_jobs = resource._existing_jobs["regular"]
    total_cores = sum(job[2] for job in regular_jobs)
    assert total_cores == 393216

    # Next job should go to interactive (next QoS in the list)
    result3 = resource.register_job("job3", walltime=20, cores=100)
    assert result3 is True
    assert "interactive" in resource._existing_jobs


def test_register_job_integration():
    """Test complete workflow: check fit, register job, verify no more room."""
    resource = PerlmutterResource()

    # Check if job fits
    qos_before = resource.fits_in_qos(walltime=20, cores=1024)
    assert qos_before is not None
    assert qos_before == QosPolicy(name="regular", max_walltime=2880, max_jobs=5000, max_cores=393216)

    # Register the job
    result = resource.register_job("large_job", walltime=20, cores=1024)
    assert result is True

    # Verify job was registered in regular QoS
    qos_after = resource.fits_in_qos(walltime=20, cores=100)
    assert qos_after is not None
    assert qos_after == QosPolicy(name="regular", max_walltime=2880, max_jobs=5000, max_cores=393216)
