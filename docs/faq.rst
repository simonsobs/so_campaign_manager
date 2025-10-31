FAQ and Troubleshooting
=======================

This document provides answers to frequently asked questions and solutions to common problems.

Frequently Asked Questions
---------------------------

General Questions
~~~~~~~~~~~~~~~~~

**Q: What is SO Campaign Manager?**

A: SO Campaign Manager is a workflow orchestration system designed for running mapmaking campaigns on HPC systems. It handles workflow scheduling, resource allocation, SLURM job submission, and monitoring for Simons Observatory data analysis.

**Q: Which HPC systems are supported?**

A: Currently, SO Campaign Manager is optimized for Tiger 3 (Princeton's HPC cluster), but it can be adapted to other SLURM-based HPC systems by creating custom Resource classes.

**Q: What is the difference between a workflow and a campaign?**

A: A **workflow** is a single computational task (e.g., one mapmaking job). A **campaign** is a collection of workflows that are scheduled and executed together to meet a deadline.

**Q: Can I run campaigns locally for testing?**

A: Yes, use ``execution_schema = "local"`` in your configuration, or use the ``--dry-run`` flag to test without actual execution.

Configuration Questions
~~~~~~~~~~~~~~~~~~~~~~~

**Q: Why do I need to use** ``file:///`` **prefix for paths?**

A: The ``file:///`` prefix is a URI scheme that explicitly indicates a local file path. This allows the system to potentially support other URI schemes (e.g., ``http://``, ``s3://``) in the future.

**Q: What time formats are supported for deadline and runtime?**

A: Supported formats include:

* ``"30m"`` - 30 minutes
* ``"2h"`` - 2 hours
* ``"3d"`` - 3 days
* ``"1w"`` - 1 week
* Also accepts raw minutes as integer: ``deadline = 240`` (240 minutes)

**Q: How do I configure workflows that run in multiple stages?**

A: Use comma-separated values for multi-stage parameters:

.. code-block:: toml

   maxiter = "200,200"     # 200 iterations per stage
   downsample = "4,2"      # Downsample factors per stage

**Q: Can I use environment variables in configuration files?**

A: TOML doesn't natively support environment variable expansion. Use a pre-processing script or template system (like Jinja2) if you need dynamic values.

**Q: How do I specify different resources for different workflows?**

A: Each workflow section can have its own ``resources`` subsection:

.. code-block:: toml

   [campaign.ml-mapmaking]
   # ... workflow config

   [campaign.ml-mapmaking.resources]
   ranks = 32
   memory = "120000"

   [campaign.ml-null-tests.mission-tests]
   # ... workflow config

   [campaign.ml-null-tests.mission-tests.resources]
   ranks = 16
   memory = "60000"

Resource and Scheduling Questions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Q: How does the system select the QoS tier?**

A: The system automatically selects the lowest QoS tier that can accommodate your ``runtime`` estimate. For example, if runtime is ``"3h"``, it will select ``short`` (max 24h) rather than ``medium`` (max 3d).

**Q: What happens if my workflow exceeds the estimated runtime?**

A: The SLURM scheduler will terminate the job. Always add a safety buffer (20-50%) to your runtime estimates.

**Q: How many cores/memory should I allocate?**

A: General guidelines:

* **Ranks**: ~1 rank per 2-4 GB of data
* **Threads**: 4-16 per rank (diminishing returns beyond 16)
* **Memory**: 2x your data size + overhead
* **Runtime**: Actual expected time + 50% buffer

Start conservative and refine based on actual usage.

**Q: Can I limit the total resources used by a campaign?**

A: Yes, use the ``requested_resources`` parameter:

.. code-block:: toml

   [campaign]
   requested_resources = 3359  # Total core-hours

The planner will optimize scheduling within this budget.

**Q: What is the HEFT algorithm?**

A: HEFT (Heterogeneous Earliest Finish Time) is a scheduling algorithm that:

1. Ranks workflows by priority (computation + communication costs)
2. Assigns each workflow to resources that minimize finish time
3. Respects dependencies between workflows
4. Optimizes for minimal total campaign time (makespan)

Workflow Questions
~~~~~~~~~~~~~~~~~~

**Q: What workflows are available?**

A: Built-in workflows include:

* ``ml-mapmaking`` - Maximum likelihood mapmaking
* ``sat-sims`` - SAT simulations
* ``ml-null-tests.mission-tests`` - Time-based null tests
* ``ml-null-tests.wafer-tests`` - Detector-based null tests
* ``ml-null-tests.direction-tests`` - Scan direction null tests
* ``ml-null-tests.pwv-tests`` - PWV-based null tests
* ``ml-null-tests.day-night-tests`` - Day/night null tests
* ``ml-null-tests.elevation-tests`` - Elevation null tests
* ``ml-null-tests.moon-close-tests`` - Moon proximity null tests
* ``ml-null-tests.moonrise-set-tests`` - Moonrise/set null tests
* ``ml-null-tests.sun-close-tests`` - Sun proximity null tests

**Q: How do I create a custom workflow?**

A: See :doc:`advanced_topics` for detailed instructions on creating custom workflows.

**Q: What does** ``tiled = 1`` **do?**

A: Tiled processing breaks the sky area into smaller tiles that are processed independently. This:

* Reduces memory requirements
* Enables parallelization across tiles
* May increase total runtime due to overhead

Use tiled processing for very large sky areas.

**Q: What are null tests and why are they important?**

A: Null tests validate mapmaking by creating maps from data splits (e.g., first half vs. second half of observations). The difference map (null map) should be consistent with noise. Large signal in null maps indicates systematic errors.

Execution and Monitoring Questions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Q: How do I monitor campaign progress?**

A: Several methods:

1. Campaign manager logs to stdout
2. Check SLURM queue: ``squeue -u $USER``
3. Check RADICAL-Pilot logs: ``~/radical.pilot.sandbox/``
4. Monitor output directory for completed files

**Q: Can I cancel a running campaign?**

A: Yes, use Ctrl+C to stop the campaign manager, then cancel SLURM jobs:

.. code-block:: bash

   # Cancel all your jobs
   scancel -u $USER

   # Cancel specific job
   scancel <job_id>

**Q: How do I check if a workflow completed successfully?**

A: Check:

1. Campaign manager logs for completion message
2. SLURM job status: ``sacct -j <job_id>``
3. Output files in the configured output directory
4. RADICAL-Pilot task logs for errors

**Q: Can I resume a failed campaign?**

A: Currently, campaigns don't support automatic resume. You need to:

1. Identify which workflows completed
2. Remove completed workflows from configuration
3. Rerun campaign with remaining workflows

Error and Debugging Questions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Q: What does "ValidationError: field required" mean?**

A: A required parameter is missing from your configuration. Check the error message for the field name and add it to your TOML file.

**Q: Why am I getting "FileNotFoundError"?**

A: Common causes:

* Path is not absolute
* Missing ``file:///`` prefix
* File doesn't exist
* File not accessible from compute nodes
* Typo in path

**Q: What does "QoS not available" mean?**

A: Your estimated runtime exceeds all available QoS tiers, or the specified QoS doesn't exist on the target resource. Check your runtime estimate and QoS name.

**Q: Why is my job stuck in pending state?**

A: Common reasons:

* Resource request too large (reduce nodes/cores)
* QoS limits reached (too many jobs in queue)
* System maintenance
* Account limits exceeded

Check with: ``squeue -j <job_id> --start``

Troubleshooting Guide
---------------------

Configuration Errors
~~~~~~~~~~~~~~~~~~~~

**Problem: TOML Syntax Error**

.. code-block:: text

   Error: Invalid TOML syntax at line 15

**Solution:**

* Validate TOML syntax using an online validator
* Check for:

  * Unmatched quotes
  * Missing closing brackets
  * Invalid escape sequences
  * Duplicate section headers

**Problem: Pydantic Validation Error**

.. code-block:: text

   ValidationError: 1 validation error for Workflow
   context
     field required (type=value_error.missing)

**Solution:**

Add the missing field to your configuration:

.. code-block:: toml

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"

**Problem: Invalid Time Format**

.. code-block:: text

   Error: Cannot parse time string: '2hrs'

**Solution:**

Use correct format: ``"2h"`` (not ``"2hrs"``)

Resource Allocation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem: Out of Memory (OOM)**

.. code-block:: text

   [ERROR] Job failed: Out of memory

**Solution:**

1. Check actual memory usage from SLURM:

   .. code-block:: bash

      sacct -j <job_id> --format=JobID,MaxRSS,ReqMem

2. Increase memory allocation:

   .. code-block:: toml

      [campaign.ml-mapmaking.resources]
      memory = "240000"  # Increase from previous value

3. Or reduce data chunk size:

   .. code-block:: toml

      chunk_nobs = 5  # Reduce from 10

**Problem: Job Timeout**

.. code-block:: text

   [ERROR] Job terminated: TIMEOUT

**Solution:**

1. Check actual runtime from SLURM:

   .. code-block:: bash

      sacct -j <job_id> --format=JobID,Elapsed,Timelimit

2. Increase runtime estimate:

   .. code-block:: toml

      [campaign.ml-mapmaking.resources]
      runtime = "8h"  # Increase with buffer

**Problem: Node Allocation Failed**

.. code-block:: text

   [ERROR] SLURM reject: Requested node configuration not available

**Solution:**

* Reduce nodes requested
* Check node availability: ``sinfo``
* Use appropriate partition
* Check account limits

Execution Errors
~~~~~~~~~~~~~~~~

**Problem: Command Not Found**

.. code-block:: text

   [ERROR] /bin/bash: so-site-pipeline: command not found

**Solution:**

1. Load required modules in environment:

   .. code-block:: toml

      [campaign.ml-mapmaking.environment]
      MODULE_LOAD = "module load python/3.11"

2. Or use full path to executable:

   .. code-block:: toml

      [campaign.ml-mapmaking]
      executable = "/full/path/to/so-site-pipeline"

**Problem: Permission Denied**

.. code-block:: text

   [ERROR] Permission denied: /path/to/output

**Solution:**

1. Check directory exists and is writable:

   .. code-block:: bash

      ls -ld /path/to/output

2. Create directory if needed:

   .. code-block:: bash

      mkdir -p /path/to/output

3. Check file system is mounted on compute nodes

**Problem: Import Error**

.. code-block:: text

   ImportError: No module named 'sotodlib'

**Solution:**

1. Ensure Python environment is activated:

   .. code-block:: toml

      [campaign.ml-mapmaking.environment]
      PYTHONPATH = "/path/to/sotodlib:$PYTHONPATH"

2. Or load module:

   .. code-block:: toml

      [campaign.ml-mapmaking.environment]
      MODULE_LOAD = "module load sotodlib"

Data Errors
~~~~~~~~~~~

**Problem: Context File Not Found**

.. code-block:: text

   FileNotFoundError: /path/to/context.yaml

**Solution:**

* Use absolute path with ``file:///`` prefix
* Verify file exists on compute nodes
* Check file permissions

**Problem: Invalid Query**

.. code-block:: text

   [ERROR] SQL syntax error in query

**Solution:**

* Validate query syntax
* Use query file for complex queries:

  .. code-block:: toml

     query = "file:///path/to/query.txt"

* Test query against context file manually

**Problem: No Data Matches Query**

.. code-block:: text

   [WARNING] Query returned 0 observations

**Solution:**

* Verify query syntax
* Check observation IDs exist in context
* Broaden query criteria

RADICAL-Pilot Errors
~~~~~~~~~~~~~~~~~~~~~

**Problem: Pilot Failed to Start**

.. code-block:: text

   [ERROR] Pilot submission failed

**Solution:**

1. Check SLURM job logs:

   .. code-block:: bash

      cat ~/radical.pilot.sandbox/rp.session.*/pilot.*/pilot.log

2. Verify resource configuration
3. Check SLURM account is valid
4. Ensure adequate resources available

**Problem: Task Submission Failed**

.. code-block:: text

   [ERROR] Task submission to pilot failed

**Solution:**

* Check pilot is running: ``squeue -u $USER``
* Verify task description is valid
* Check pilot has sufficient resources for task

Performance Issues
~~~~~~~~~~~~~~~~~~

**Problem: Slow Execution**

**Diagnosis:**

.. code-block:: bash

   # Check CPU utilization
   ssh <compute-node>
   top

   # Check I/O wait
   iostat -x 5

**Solutions:**

* If CPU idle: Increase parallelism (ranks/threads)
* If I/O bound: Use faster storage, reduce I/O operations
* If memory bandwidth limited: Reduce threads per rank

**Problem: Inefficient Scheduling**

**Diagnosis:**

* Jobs running sequentially instead of parallel
* Long idle times between jobs

**Solution:**

* Review workflow dependencies
* Check deadline is realistic
* Consider manual scheduling for small campaigns

Debugging Workflow
------------------

Step-by-Step Debugging Process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Validate Configuration**

   .. code-block:: bash

      socm -t campaign.toml --dry-run

2. **Check File Paths**

   .. code-block:: bash

      ls -l /path/to/context.yaml
      ls -ld /path/to/output

3. **Test on Small Dataset**

   Create minimal configuration with single observation

4. **Monitor SLURM**

   .. code-block:: bash

      # Watch job queue
      watch -n 5 'squeue -u $USER'

      # Check job details
      scontrol show job <job_id>

5. **Check Logs**

   * Campaign manager stdout
   * SLURM job output files
   * RADICAL-Pilot logs
   * Application logs in output directory

6. **Verify Environment**

   SSH to compute node and verify:

   * Modules loaded
   * Environment variables set
   * Executables in PATH
   * Data files accessible

Common Patterns
---------------

Pattern: Incremental Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start small and scale up:

1. **Single observation, minimal iterations**

   .. code-block:: toml

      maxiter = "10"
      query = "obs_id='single_obs'"

2. **Small dataset, full iterations**

   .. code-block:: toml

      maxiter = "100"
      query = "file:///path/to/small_query.txt"

3. **Full dataset**

   .. code-block:: toml

      maxiter = "200,200"
      query = "file:///path/to/full_query.txt"

Pattern: Resource Tuning
~~~~~~~~~~~~~~~~~~~~~~~~~

Systematically find optimal resources:

1. Run with conservative estimates
2. Monitor actual usage
3. Adjust based on observations:

   * Memory: Actual max + 20%
   * Runtime: Actual + 50%
   * Cores: Test weak scaling

4. Document findings for future campaigns

Pattern: Error Recovery
~~~~~~~~~~~~~~~~~~~~~~~

When campaigns fail:

1. **Identify failed workflows**

   Check logs and output directories

2. **Determine cause**

   Read error messages, check resource usage

3. **Fix configuration**

   Adjust based on cause (more memory, longer runtime, etc.)

4. **Remove completed workflows**

   Comment out successful workflows in TOML

5. **Rerun failed workflows**

   Run campaign with updated configuration

Getting Help
------------

When to Seek Help
~~~~~~~~~~~~~~~~~

Seek help if:

* Error messages are unclear
* Issue persists after troubleshooting
* Suspected bug in SO Campaign Manager
* Need feature not available

How to Report Issues
~~~~~~~~~~~~~~~~~~~~

When reporting issues, include:

1. **Minimal reproducible example**

   * Simplified configuration
   * Sample data if possible

2. **Error messages**

   * Full error output
   * Relevant log excerpts

3. **Environment information**

   * SO Campaign Manager version
   * Python version
   * HPC system details
   * SLURM version

4. **What you've tried**

   * Troubleshooting steps taken
   * Configuration changes attempted

Where to Get Help
~~~~~~~~~~~~~~~~~

* **Documentation**: Check :doc:`index` for comprehensive guides
* **GitHub Issues**: https://github.com/simonsobs/so_campaign_manager/issues
* **HPC Support**: Contact your HPC center for SLURM/system issues
* **Community**: Simons Observatory Slack or mailing lists

Tips and Best Practices
------------------------

Configuration Tips
~~~~~~~~~~~~~~~~~~

1. **Use version control** for configuration files
2. **Document your configurations** with comments
3. **Template common patterns** for reuse
4. **Test configurations** before production runs
5. **Keep configurations DRY** using subcampaigns

Resource Management Tips
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Start conservative** with resource estimates
2. **Monitor actual usage** and adjust
3. **Add safety buffers** (20% memory, 50% runtime)
4. **Use appropriate QoS** for job priority
5. **Consider cost** (core-hours) vs. time tradeoff

Workflow Organization Tips
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Group related workflows** using subcampaigns
2. **Name workflows descriptively**
3. **Document workflow purpose** in configuration
4. **Test workflows individually** before campaigns
5. **Track workflow versions** for reproducibility

Debugging Tips
~~~~~~~~~~~~~~

1. **Enable verbose logging** during debugging
2. **Use dry-run mode** to validate configuration
3. **Test incrementally** from simple to complex
4. **Keep logs** for successful runs (for comparison)
5. **Document solutions** to recurring issues

Additional Resources
--------------------

* :doc:`tutorial` - Step-by-step tutorials
* :doc:`user_guide` - Comprehensive user documentation
* :doc:`workflows` - Workflow-specific documentation
* :doc:`architecture` - System architecture and design
* :doc:`advanced_topics` - Advanced features and customization
* :doc:`developer_guide` - Contributing and development

Glossary
--------

**Campaign**
   Collection of workflows scheduled together

**Workflow**
   Single computational task

**QoS (Quality of Service)**
   SLURM policy defining resource limits

**HEFT**
   Heterogeneous Earliest Finish Time scheduling algorithm

**Rank**
   MPI process

**Thread**
   OpenMP thread within a process

**Makespan**
   Total time to complete all workflows

**DAG**
   Directed Acyclic Graph (workflow dependencies)

**Enactor**
   Execution backend (e.g., RADICAL-Pilot)

**Planner**
   Scheduling algorithm (e.g., HEFT)

**Bookkeeper**
   Main orchestration component

**Null Test**
   Validation test using data splits

**Pilot Job**
   SLURM allocation managed by RADICAL-Pilot

**Task**
   RADICAL-Pilot unit of work (workflow instance)
