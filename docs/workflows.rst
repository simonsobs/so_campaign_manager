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

Small Aperture Telescope (SAT) simulation workflows for generating synthetic observations
using ``toast_so_sim``.

**Purpose:** Create realistic simulated timestreams for validation and systematics studies.

**Configuration Example:**

.. code-block:: toml

   [campaign.sat-sims]
   output_dir = "/path/to/output"
   schedule = "/path/to/schedule.txt"
   bands = "SAT_f090"
   wafer_slots = "w25"
   sample_rate = 37
   sim_noise = false
   scan_map = false
   sim_atmosphere = false
   sim_sss = false
   sim_hwpss = false

**Key Parameters:**

* ``output_dir``: Directory for simulation output
* ``schedule``: Observation schedule file
* ``bands``: Frequency band (e.g. ``SAT_f090``, ``SAT_f150``)
* ``wafer_slots``: Wafer slot identifier (e.g. ``w25``)
* ``sample_rate``: Detector sample rate in Hz (default: 37)
* ``sim_noise``: Enable noise simulation (boolean)
* ``scan_map``: Enable map scanning (boolean)
* ``sim_atmosphere``: Enable atmosphere simulation (boolean)
* ``sim_sss``: Enable spin-synchronous signal simulation (boolean)
* ``sim_hwpss``: Enable HWP synchronous signal simulation (boolean)
* ``pixels_healpix_radec_nside``: HEALPix resolution (default: 512)

Power Spectra
~~~~~~~~~~~~~

Power spectrum estimation workflow using PSpipe.

**Purpose:** Compute power spectra from maps produced by the mapmaking pipeline.

**Configuration Example:**

.. code-block:: toml

   [campaign.power-spectra]
   subcommand = "/path/to/script.py"
   script_args = ["/path/to/paramfile.dict"]
   script_flags = ["simulate-syst", "simulate-lens"]

**Key Parameters:**

* ``subcommand``: Path to the PSpipe Python script to run
* ``script_args``: Positional arguments passed to the script (list)
* ``script_flags``: Boolean flags passed as ``--flag`` (list)

**Resource Requirements:**

* Scales with the number of map products being cross-correlated
* Some stages (e.g. mode-coupling matrix) are MPI-parallel and benefit from many ranks

ML Null Tests
~~~~~~~~~~~~~

Statistical tests to validate mapmaking results by creating maps from data splits.

**Purpose:** Detect systematic errors and validate noise models by checking that null maps (differences between splits) are consistent with noise.

All null tests share the following common parameters:

* ``chunk_nobs``: Number of observations per chunk used to define splits
* ``context``, ``area``, ``output_dir``, ``query``: Same as ML Mapmaking

**Types of Null Tests:**

Mission Tests
^^^^^^^^^^^^^

Splits observations in time to test for time-dependent systematics.

.. code-block:: toml

   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10
   nsplits = 8

Observations are sorted by timestamp, grouped into chunks of ``chunk_nobs``, and
distributed across ``nsplits`` splits in a time-interleaved fashion.

Wafer Tests
^^^^^^^^^^^

Splits observations by detector wafer to test for detector-dependent systematics.

.. code-block:: toml

   [campaign.ml-null-tests.wafer-tests]
   chunk_nobs = 10
   nsplits = 8

Observations are grouped by wafer slot and maps are produced per-wafer for comparison.

Direction Tests
^^^^^^^^^^^^^^^

Splits observations by scan direction (rising, setting, or middle azimuth) to test for
scan-synchronous systematics. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.direction-tests]
   chunk_nobs = 10

Observations are classified by azimuth center into rising (az < 180°), setting (az > 180°),
or middle (az ≈ 180°) groups, and time-interleaved splits are created within each group.

PWV Tests
^^^^^^^^^

Splits observations by precipitable water vapour (PWV) level to test for
atmosphere-dependent systematics.

.. code-block:: toml

   [campaign.ml-null-tests.pwv-tests]
   chunk_nobs = 10
   nsplits = 2

Observations are ordered by PWV value and interleaved into splits, separating
low-PWV from high-PWV conditions.

Day/Night Tests
^^^^^^^^^^^^^^^

Splits observations into daytime and nighttime subsets to test for solar-related
systematics.

.. code-block:: toml

   [campaign.ml-null-tests.day-night-tests]
   chunk_nobs = 10
   nsplits = 2

Observations are classified as day or night based on their timestamp and maps are
produced separately for each condition.

Elevation Tests
^^^^^^^^^^^^^^^

Splits observations by telescope elevation to test for elevation-dependent systematics
such as ground pickup or atmospheric gradients.

.. code-block:: toml

   [campaign.ml-null-tests.elevation-tests]
   chunk_nobs = 10
   nsplits = 2

Observations are sorted by elevation center and distributed across splits.

Moon Rise/Set Tests
^^^^^^^^^^^^^^^^^^^

Splits observations by whether the Moon is rising or setting during the observation,
to test for Moon-related contamination correlated with lunar phase angle.

.. code-block:: toml

   [campaign.ml-null-tests.moonrise-set-tests]
   chunk_nobs = 10
   nsplits = 2

Moon Close Tests
^^^^^^^^^^^^^^^^

Splits observations by proximity to the Moon to test for near-field Moon sidelobe
contamination.

.. code-block:: toml

   [campaign.ml-null-tests.moon-close-tests]
   chunk_nobs = 10
   nsplits = 2

Sun Close Tests
^^^^^^^^^^^^^^^

Splits observations by proximity to the Sun to test for near-field Sun sidelobe
contamination.

.. code-block:: toml

   [campaign.ml-null-tests.sun-close-tests]
   chunk_nobs = 10
   nsplits = 2

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

* **Dependency resolution** - Ensures workflows run in the correct order
* **Resource optimization** - Schedules dependent workflows as early as possible using HEFT

For TOML-based campaigns, subcampaigns provide a grouping mechanism. For explicit
stage-by-stage dependency graphs, use the DAG YAML format:

.. code-block:: yaml

   stages:
     preprocess:
       executable: python -u
       script: preprocess.py
       depends: null
       resources:
         memory: 48G
         ranks: 1
         threads: 4
         runtime: 10m

     mapmaking:
       executable: python -u
       script: mapmaking.py
       depends:
         - preprocess
       resources:
         ranks: 14
         threads: 8
         memory: 128G
         runtime: 60m

     spectra:
       executable: python -u
       script: spectra.py
       depends:
         - mapmaking
       resources:
         ranks: 4
         threads: 4
         memory: 32G
         runtime: 20m

See the :doc:`user_guide` DAG section and ``examples/dag.yml`` for a full annotated example.

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
