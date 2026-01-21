Workflows
=========

SO Campaign Manager supports several types of workflows for different analysis tasks.

Overview
--------

Workflows are the fundamental units of computation in SO Campaign Manager. Each workflow:

* Defines a specific analysis task
* Specifies resource requirements
* Includes environment configuration
* Can have dependencies on other workflows

Available Workflows
-------------------

ML Mapmaking
~~~~~~~~~~~~

Maximum likelihood mapmaking creates maps from time-ordered data using iterative algorithms.

**Purpose:** Generate high-quality maps with proper noise modeling and systematics mitigation.

**Configuration Example:**

.. code-block:: toml

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output"
   bands = "f090"
   wafer = "ws0"
   comps = "TQU"
   maxiter = 10
   query = "obs_id='1575600533.1575611468.ar5_1'"
   tiled = 1
   site = "act"

**Key Parameters:**

* ``context``: Context file defining data selection and processing parameters
* ``area``: FITS file defining the sky area to map
* ``bands``: Frequency bands to process ("f090", "f150", etc.)
* ``wafer``: Detector wafer identifier
* ``comps``: Map components ("T" for temperature only, "TQU" for temperature and polarization)
* ``maxiter``: Maximum number of iterations for convergence
* ``query``: SQL-like query for data selection
* ``tiled``: Whether to use tiled processing (0 or 1)

**Resource Requirements:**

* Memory-intensive (typically 64-128 GB per process)
* Can benefit from multiple cores for linear algebra operations
* Disk I/O intensive for large datasets

SAT Simulation
~~~~~~~~~~~~~~

Small Aperture Telescope (SAT) simulation workflows for generating synthetic observations.

**Purpose:** Create realistic simulated timestreams for testing and validation.

**Configuration:** Similar to ML mapmaking but with simulation-specific parameters.

ML Null Tests
~~~~~~~~~~~~~

Statistical tests to validate mapmaking results by creating maps from data splits.

**Purpose:** Detect systematic errors and validate noise models by checking that null maps (differences between splits) are consistent with noise.

**Types of Null Tests:**

Mission Tests
^^^^^^^^^^^^^

Test for time-dependent systematics by splitting data in time.

.. code-block:: toml

   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10  # Chunk size in days
   nsplits = 8      # Number of splits (power of 2)

**Process:**

1. Divide observation time into chunks
2. Randomly assign chunks to splits
3. Create maps from each split
4. Analyze differences between splits

Wafer Tests
^^^^^^^^^^^

Test for detector-dependent systematics by splitting data by detector wafer.

.. code-block:: toml

   [campaign.ml-null-tests.wafer-tests]
   chunk_nobs = 10  # Chunk size in days
   nsplits = 8      # Number of splits

**Process:**

1. Group detectors by wafer or other characteristics
2. Create maps from different detector groups
3. Analyze differences for systematic effects

Creating Custom Workflows
--------------------------

To create a new workflow type:

1. **Inherit from base Workflow class:**

.. code-block:: python

   from socm.core.models import Workflow

   class MyCustomWorkflow(Workflow):
       # Define additional parameters
       custom_param: str
       threshold: float = 0.5

2. **Implement required methods:**

.. code-block:: python

   def get_command(self, **kwargs) -> str:
       """Return the command to execute."""
       return f"{self.executable} {self.subcommand}"

   def get_arguments(self, **kwargs) -> str:
       """Return command arguments."""
       return f"--param {self.custom_param} --threshold {self.threshold}"

3. **Register the workflow:**

.. code-block:: python

   from socm.workflows import registered_workflows

   registered_workflows['my-custom'] = MyCustomWorkflow

Workflow Dependencies
---------------------

Workflows can depend on outputs from other workflows. The campaign manager handles:

* **Dependency resolution** - Ensures workflows run in correct order
* **Data flow** - Passes outputs from one workflow to inputs of another
* **Resource optimization** - Schedules dependent workflows efficiently

Configuration via subcampaigns allows complex workflow graphs:

.. code-block:: toml

   [campaign.preprocessing]
   # First stage workflow

   [campaign.mapmaking]
   # Second stage that depends on preprocessing
   depends_on = ["preprocessing"]

Best Practices
--------------

Resource Sizing
~~~~~~~~~~~~~~~

* **Memory:** Allocate 20-50% more than estimated need
* **Runtime:** Set conservative estimates to avoid queue timeouts
* **Cores:** Balance between parallelization and memory per core

Data Management
~~~~~~~~~~~~~~~

* Use fast local storage for temporary files
* Ensure output directories have sufficient space
* Clean up intermediate files when possible

Configuration
~~~~~~~~~~~~~

* Use descriptive workflow names for tracking
* Document custom parameters in configuration files
* Test workflows on small datasets first

Monitoring
~~~~~~~~~~

* Check log files for workflow progress
* Monitor resource usage to optimize future runs
* Validate outputs before proceeding to dependent workflows

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Memory Errors:**
   * Increase memory allocation
   * Reduce data chunk size
   * Use tiled processing for large areas

**Timeout Errors:**
   * Increase runtime estimates
   * Check for hung processes
   * Optimize algorithm parameters

**Dependency Errors:**
   * Verify input file paths
   * Check workflow ordering
   * Ensure dependent outputs exist

**Environment Issues:**
   * Verify environment variables
   * Check module availability
   * Validate file permissions

Performance Tips
~~~~~~~~~~~~~~~~

* Use SSD storage for temporary files
* Optimize number of MPI ranks vs threads
* Consider memory bandwidth limitations
* Profile workflows to identify bottlenecks
