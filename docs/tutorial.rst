Tutorial
========

This tutorial will guide you through using SO Campaign Manager step-by-step, from basic usage to advanced configurations.

Tutorial Overview
-----------------

In this tutorial, you will learn:

1. How to set up your first campaign
2. How to configure workflows and resources
3. How to run and monitor campaigns
4. How to work with null tests
5. How to optimize resource usage
6. How to troubleshoot common issues

Prerequisites
-------------

Before starting, ensure you have:

* SO Campaign Manager installed (see :doc:`installation`)
* Access to an HPC system (e.g., Tiger 3)
* Basic understanding of SLURM job scheduling
* Sample data for SO mapmaking (context files, area definitions, etc.)

Tutorial 1: Your First Campaign
--------------------------------

Let's create a simple campaign with a single ML mapmaking workflow.

Step 1: Understand the Campaign Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A campaign consists of:

* **Campaign configuration** - Deadline and global settings
* **Workflows** - Analysis tasks to execute
* **Resources** - HPC resource requirements per workflow
* **Environment** - Environment variables for execution

Step 2: Create a Basic Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``my_first_campaign.toml``:

.. code-block:: toml

   # Campaign-level configuration
   [campaign]
   deadline = "4h"  # Complete within 4 hours
   resource = "tiger3"  # Target HPC resource
   execution_schema = "remote"  # Execute on remote HPC

   # ML Mapmaking workflow configuration
   [campaign.ml-mapmaking]
   # Input files (use absolute paths)
   context = "file:///path/to/your/context.yaml"
   area = "file:///path/to/your/area.fits"
   output_dir = "/path/to/output"

   # Analysis parameters
   bands = "f090"          # Frequency band to process
   maxiter = "100"         # Maximum iterations
   query = "obs_id='your_observation_id'"  # Data selection query
   tiled = 0               # Don't use tiled processing
   site = "so_lat"         # Observatory site

   # Resource requirements for this workflow
   [campaign.ml-mapmaking.resources]
   ranks = 1               # Number of MPI ranks
   threads = 32            # Number of OpenMP threads
   memory = "80000"        # Memory in MB (80 GB)
   runtime = "2h"          # Expected runtime

   # Environment variables
   [campaign.ml-mapmaking.environment]
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

.. note::
   **Important:** All file paths in the configuration must be **absolute paths** starting with ``file:///``.

Step 3: Validate Your Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before running, let's understand what each parameter means:

**Campaign Parameters:**

* ``deadline``: Maximum time for the entire campaign to complete

  * Format: ``"2h"`` (2 hours), ``"30m"`` (30 minutes), ``"3d"`` (3 days)
  * The planner will optimize workflow scheduling to meet this deadline

* ``resource``: Target HPC system (currently only ``"tiger3"`` is supported)

* ``execution_schema``: How to execute (``"remote"`` for HPC, ``"local"`` for testing)

**Workflow Parameters:**

* ``context``: Path to SOTODLIB context YAML file defining data structure
* ``area``: Path to FITS file defining the sky area to map
* ``output_dir``: Directory where output maps will be written
* ``bands``: Frequency band(s) to process (``"f090"``, ``"f150"``, or ``"f090,f150"``)
* ``maxiter``: Maximum iterations for convergence (typically 100-200)
* ``query``: SQL-like query to select observations from context
* ``tiled``: Whether to use tiled processing (0 = no, 1 = yes)
* ``site``: Observatory site identifier (``"so_lat"`` or ``"so_sat"``)

**Resource Parameters:**

* ``ranks``: Number of MPI processes
* ``threads``: Number of OpenMP threads per process
* ``memory``: Total memory requirement in MB
* ``runtime``: Expected execution time (used for QoS selection)

Step 4: Run Your Campaign
~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the campaign using the command-line interface:

.. code-block:: bash

   socm -t my_first_campaign.toml

You should see output similar to:

.. code-block:: text

   [INFO] Loading campaign configuration from my_first_campaign.toml
   [INFO] Validating configuration...
   [INFO] Creating 1 workflow(s)
   [INFO] Planning campaign with deadline: 240 minutes
   [INFO] Selected QoS: medium (max walltime: 4320 minutes)
   [INFO] Submitting workflows to SLURM...
   [INFO] Campaign execution started
   [INFO] Monitoring workflow progress...

Step 5: Monitor Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~

The campaign manager will:

1. Parse your configuration
2. Create workflow instances
3. Plan the execution schedule
4. Submit jobs to SLURM
5. Monitor execution and report progress

You can monitor SLURM jobs directly:

.. code-block:: bash

   # Check your SLURM queue
   squeue -u $USER

   # Monitor specific job
   scontrol show job <job_id>

Step 6: Check Output
~~~~~~~~~~~~~~~~~~~~~

Once complete, check your output directory:

.. code-block:: bash

   ls -lh /path/to/output/

You should find:

* Output maps (FITS files)
* Log files
* Metadata about the run

Congratulations! You've run your first campaign.

Tutorial 2: Multiple Workflows in Parallel
-------------------------------------------

Now let's create a campaign with multiple workflows that run in parallel.

Step 1: Create Multi-Workflow Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``multi_workflow_campaign.toml``:

.. code-block:: toml

   [campaign]
   deadline = "8h"
   resource = "tiger3"
   execution_schema = "remote"
   requested_resources = 1000  # Total core-hours budget

   # First workflow: f090 band
   [campaign.ml-mapmaking]
   name = "mapmaking_f090"
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output/f090"
   bands = "f090"
   maxiter = "100"
   query = "obs_id='observation_1'"
   site = "so_lat"

   [campaign.ml-mapmaking.resources]
   ranks = 32
   threads = 8
   memory = "120000"
   runtime = "3h"

Since TOML doesn't support multiple sections with the same name, you'll need to use arrays or separate workflow types. Let me show you a better approach using subcampaigns:

.. code-block:: toml

   [campaign]
   deadline = "8h"
   resource = "tiger3"
   execution_schema = "remote"

   # Common configuration for all mapmaking workflows
   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output"
   maxiter = "100"
   site = "so_lat"

   [campaign.ml-mapmaking.resources]
   ranks = 32
   threads = 8
   memory = "120000"
   runtime = "3h"

   # You can then modify the query or bands in the code
   # or use different workflow types

Step 2: Understanding Parallel Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The campaign manager automatically:

* Detects workflows that can run in parallel
* Schedules them based on resource availability
* Optimizes to meet the deadline
* Manages dependencies between workflows

Tutorial 3: Null Test Campaigns
--------------------------------

Null tests are crucial for validating mapmaking results. Let's create a comprehensive null test campaign.

Step 1: Understanding Null Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Null tests validate your mapmaking by creating maps from data splits:

* **Mission Tests**: Split by time
* **Wafer Tests**: Split by detector
* **Direction Tests**: Split by scan direction
* **PWV Tests**: Split by precipitable water vapor
* **Day/Night Tests**: Split by time of day
* **Elevation Tests**: Split by telescope elevation

Step 2: Configure Null Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``null_test_campaign.toml``:

.. code-block:: toml

   [campaign]
   deadline = "12h"
   resource = "tiger3"
   execution_schema = "remote"

   # Common configuration for all null tests
   [campaign.ml-null-tests]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output/null_tests"
   bands = "f090"
   maxiter = "100,100"  # Two iteration stages
   downsample = "4,2"   # Downsample factors for each stage
   query = "file:///path/to/query.txt"
   tiled = 1
   site = "so_lat"

   # Mission tests: time-based splits
   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10      # Chunk size in days
   nsplits = 4          # Number of splits (must be power of 2)

   [campaign.ml-null-tests.mission-tests.resources]
   ranks = 35
   threads = 8
   memory = "2400000"   # 2.4 TB
   runtime = "4h"

   # Wafer tests: detector-based splits
   [campaign.ml-null-tests.wafer-tests]
   chunk_nobs = 10
   nsplits = 4

   [campaign.ml-null-tests.wafer-tests.resources]
   ranks = 12
   threads = 8
   memory = "80000"
   runtime = "4h"

   # Direction tests: scan direction splits
   [campaign.ml-null-tests.direction-tests]
   chunk_nobs = 10
   nsplits = 4

   [campaign.ml-null-tests.direction-tests.resources]
   ranks = 17
   threads = 8
   memory = "80000"
   runtime = "4h"

Step 3: Understanding Subcampaign Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Notice how the null test workflows inherit common configuration:

* ``context``, ``area``, ``bands``, etc. are defined once in ``[campaign.ml-null-tests]``
* Each specific test (``mission-tests``, ``wafer-tests``, etc.) inherits these
* Specific tests only need to define their unique parameters

This follows the **DRY principle** (Don't Repeat Yourself).

Step 4: Run Null Test Campaign
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   socm -t null_test_campaign.toml

The campaign manager will:

1. Create 3 null test workflows (mission, wafer, direction)
2. Schedule them for parallel execution
3. Monitor all workflows
4. Report completion status

Tutorial 4: Resource Optimization
----------------------------------

Learn how to optimize resource usage for cost-effective campaigns.

Step 1: Understanding Resource Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The key resource parameters affect both performance and cost:

**Ranks (MPI Processes):**

* More ranks → faster for I/O-heavy tasks
* Diminishing returns beyond data parallelism limit
* Rule of thumb: 1 rank per ~2-4 GB of data

**Threads (OpenMP):**

* More threads → faster for compute-heavy tasks
* Limited by memory bandwidth
* Rule of thumb: 4-16 threads per rank

**Memory:**

* Must accommodate: data + working set + overhead
* Rule of thumb: 2x data size for mapmaking
* Monitor actual usage and adjust

**Runtime:**

* Affects QoS selection (queue priority)
* Overestimate to avoid timeout
* Underestimate wastes resources if too conservative

Step 2: QoS Tiers on Tiger
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tiger has several QoS tiers with different limits:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - QoS Tier
     - Max Walltime
     - Max Jobs
     - Best For
   * - test
     - 60 minutes
     - Limited
     - Quick tests, debugging
   * - vshort
     - 5 hours
     - Many
     - Small workflows
   * - short
     - 24 hours
     - Many
     - Standard workflows
   * - medium
     - 3 days
     - Moderate
     - Large workflows
   * - long
     - 6 days
     - Few
     - Very large workflows
   * - vlong
     - 15 days
     - Very few
     - Extremely large workflows

The campaign manager automatically selects the appropriate QoS based on your ``runtime`` estimate.

Step 3: Right-Sizing Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's optimize a workflow:

**Initial (over-allocated) configuration:**

.. code-block:: toml

   [campaign.ml-mapmaking.resources]
   ranks = 100           # Too many?
   threads = 32          # Too many?
   memory = "500000"     # 500 GB - too much?
   runtime = "10h"       # Too long?

**Steps to optimize:**

1. **Start with a small test:**

   .. code-block:: toml

      ranks = 10
      threads = 8
      memory = "100000"
      runtime = "1h"

2. **Run and monitor:**

   .. code-block:: bash

      # During execution, monitor memory usage
      ssh tiger-node-xx  # SSH to compute node
      top -u $USER

3. **Check logs for actual usage:**

   * Memory high-water mark
   * Actual walltime
   * CPU utilization

4. **Adjust based on findings:**

   * If memory maxed out → increase memory
   * If completed in 30min with 1h limit → reduce runtime
   * If CPU idle → reduce ranks or threads
   * If walltime nearly exceeded → increase runtime

**Optimized configuration:**

.. code-block:: toml

   [campaign.ml-mapmaking.resources]
   ranks = 35            # Sufficient for data size
   threads = 8           # Good balance
   memory = "2400000"    # 20% overhead over observed
   runtime = "4h"        # 50% buffer over observed

Step 4: Scaling Rules
~~~~~~~~~~~~~~~~~~~~~

**Weak Scaling (more data, same time):**

* Double data size → double ranks
* Keep threads constant
* Double memory

**Strong Scaling (same data, less time):**

* Limited by Amdahl's Law
* Doubling ranks doesn't halve time
* Test to find optimal parallelism

Tutorial 5: Advanced Configuration Patterns
--------------------------------------------

Step 1: Using Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Many workflows require specific environment variables:

.. code-block:: toml

   [campaign.ml-mapmaking.environment]
   # SOTODLIB configuration
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

   # Temporary storage
   TMPDIR = "/scratch/network/$USER/tmp"

   # Performance tuning
   OMP_NUM_THREADS = "8"
   OMP_PROC_BIND = "true"
   OMP_PLACES = "cores"

   # Debugging
   SOTODLIB_DEBUG = "1"

Step 2: Working with Query Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For complex observation selections, use query files:

**query.txt:**

.. code-block:: sql

   obs_id IN (
       'obs_1234567890.1234567900.ar5_1',
       'obs_1234567901.1234567911.ar5_1',
       'obs_1234567912.1234567922.ar5_1'
   )

**Configuration:**

.. code-block:: toml

   [campaign.ml-mapmaking]
   query = "file:///path/to/query.txt"

Step 3: Multi-Stage Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use multi-stage parameters for progressive refinement:

.. code-block:: toml

   [campaign.ml-mapmaking]
   maxiter = "200,200"      # 200 iterations in each of 2 stages
   downsample = "4,2"       # Downsample by 4x, then 2x

   # Stage 1: Coarse (4x downsampled), 200 iterations
   # Stage 2: Fine (2x downsampled), 200 iterations

This approach:

* Faster initial convergence at coarse resolution
* Refinement at higher resolution
* Better overall performance than single-stage

Tutorial 6: Monitoring and Debugging
-------------------------------------

Step 1: Understanding Log Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The campaign manager produces several types of log messages:

.. code-block:: text

   [INFO] Normal informational messages
   [WARNING] Potential issues (non-fatal)
   [ERROR] Errors that stop execution
   [DEBUG] Detailed debugging information

Step 2: Checking Workflow Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monitor SLURM jobs:

.. code-block:: bash

   # List your jobs
   squeue -u $USER

   # Detailed job info
   scontrol show job <job_id>

   # Job accounting info
   sacct -j <job_id> --format=JobID,JobName,State,Elapsed,MaxRSS

Step 3: Accessing Job Logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

RADICAL-Pilot creates detailed logs:

.. code-block:: bash

   # Find RADICAL-Pilot session directory
   ls -lrt ~/radical.pilot.sandbox/

   # Check pilot logs
   cat ~/radical.pilot.sandbox/rp.session.*/pilot.*/pilot.log

   # Check task logs
   cat ~/radical.pilot.sandbox/rp.session.*/pilot.*/task.*/task.log

Step 4: Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue: Configuration validation error**

.. code-block:: text

   [ERROR] ValidationError: field required: context

**Solution:** Check TOML syntax and ensure all required fields are present.

---

**Issue: Out of memory error**

.. code-block:: text

   [ERROR] Workflow failed: MemoryError

**Solution:** Increase ``memory`` parameter in resources section.

---

**Issue: Walltime exceeded**

.. code-block:: text

   [ERROR] Job terminated: TIMEOUT

**Solution:** Increase ``runtime`` parameter or optimize workflow.

---

**Issue: File not found**

.. code-block:: text

   [ERROR] FileNotFoundError: /path/to/context.yaml

**Solution:**

* Verify file paths are absolute
* Use ``file:///`` prefix for file URIs
* Ensure files are accessible from compute nodes

Tutorial 7: Testing Before Production
--------------------------------------

Step 1: Dry Run Mode
~~~~~~~~~~~~~~~~~~~~~

Test your configuration without submitting jobs:

.. code-block:: bash

   socm -t campaign.toml --dry-run

This will:

* Validate configuration
* Create workflow objects
* Run planning
* Show what would be executed
* **Not submit any jobs**

Step 2: Small-Scale Test
~~~~~~~~~~~~~~~~~~~~~~~~~

Before running on full dataset:

1. Create a test configuration with subset of data
2. Use shorter runtime limits
3. Use test QoS tier
4. Verify outputs are correct

**Test configuration:**

.. code-block:: toml

   [campaign]
   deadline = "1h"
   resource = "tiger3"

   [campaign.ml-mapmaking]
   # ... same configuration but with:
   query = "obs_id='single_test_observation'"  # Just one obs
   maxiter = "10"  # Fewer iterations

   [campaign.ml-mapmaking.resources]
   runtime = "30m"  # Short runtime for test QoS

Step 3: Validation Checklist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before submitting production campaigns:

☐ Configuration validates without errors

☐ File paths are correct and accessible

☐ Environment variables are set correctly

☐ Resource estimates are reasonable

☐ Output directories exist and are writable

☐ Test run completed successfully

☐ Output files are in expected format

☐ Resource usage matches estimates

Tutorial 8: Programmatic Usage
-------------------------------

For advanced use cases, use the Python API directly.

Step 1: Basic Python Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from socm.bookkeeper import Bookkeeper
   from socm.core import Campaign
   from socm.resources import TigerResource
   from socm.workflows import MLMapmakingWorkflow

   # Create workflow
   workflow = MLMapmakingWorkflow(
       name="test_mapmaking",
       executable="so-site-pipeline",
       subcommand="make-filterbin-map",
       context="/path/to/context.yaml",
       area="/path/to/area.fits",
       output_dir="/path/to/output",
       bands="f090",
       maxiter="100",
       query="obs_id='test'",
       site="so_lat",
       resources={
           "ranks": 32,
           "threads": 8,
           "memory": 120000,
           "runtime": "3h"
       }
   )

   # Create campaign
   campaign = Campaign(
       id=1,
       workflows=[workflow],
       campaign_policy="time",
       deadline=240  # minutes
   )

   # Create resource
   resource = TigerResource()

   # Execute
   bookkeeper = Bookkeeper(
       campaign=campaign,
       resources={"tiger3": resource},
       policy="time",
       target_resource="tiger3",
       deadline=240
   )

   bookkeeper.run()

Step 2: Dynamic Workflow Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate workflows programmatically:

.. code-block:: python

   from socm.workflows import MLMapmakingWorkflow

   # List of bands to process
   bands_list = ["f090", "f150", "f220"]

   # Create workflow for each band
   workflows = []
   for band in bands_list:
       wf = MLMapmakingWorkflow(
           name=f"mapmaking_{band}",
           executable="so-site-pipeline",
           subcommand="make-filterbin-map",
           context="/path/to/context.yaml",
           area="/path/to/area.fits",
           output_dir=f"/path/to/output/{band}",
           bands=band,
           maxiter="100",
           query="obs_id='test'",
           site="so_lat",
           resources={
               "ranks": 32,
               "threads": 8,
               "memory": 120000,
               "runtime": "3h"
           }
       )
       workflows.append(wf)

   # Create campaign with all workflows
   campaign = Campaign(
       id=1,
       workflows=workflows,
       campaign_policy="time"
   )

Next Steps
----------

Now that you've completed the tutorials, you can:

* Read the :doc:`user_guide` for comprehensive reference
* Explore :doc:`workflows` for detailed workflow documentation
* Check :doc:`advanced_topics` for advanced features
* Review :doc:`architecture` to understand system internals
* Consult :doc:`faq` for common questions

Congratulations on completing the tutorial! You're now ready to run production campaigns with SO Campaign Manager.
