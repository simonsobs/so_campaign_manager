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

All workflow classes inherit from :class:`~socm.core.models.Workflow` and must implement
:meth:`~socm.core.models.Workflow.get_command` and
:meth:`~socm.core.models.Workflow.get_arguments`.

Available Workflows
-------------------

ML Mapmaking
~~~~~~~~~~~~

Maximum likelihood mapmaking creates maps from time-ordered data using iterative algorithms.

**Class:** :class:`~socm.workflows.ml_mapmaking.MLMapmakingWorkflow`

**Registered key:** ``"ml-mapmaking"``

**Purpose:** Generate high-quality maps with proper noise modeling and systematics mitigation.

**Configuration Example:**

.. code-block:: toml

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output"
   preprocess_config = "file:///path/to/preprocess.yaml"
   bands = "f090"
   wafers = "ws0"
   comps = "TQU"
   maxiter = 500
   query = "obs_id='1575600533.1575611468.ar5_1'"
   tiled = 1
   site = "so_lat"

**Key Parameters:**

* ``context``: Context file defining data selection and processing parameters (``file://`` URI)
* ``area``: FITS file defining the sky area to map (``file://`` URI)
* ``preprocess_config``: Preprocessing configuration file (``file://`` URI)
* ``bands``: Frequency bands to process (``"f090"``, ``"f150"``, etc.)
* ``comps``: Map components (``"T"`` for temperature only, ``"TQU"`` for T+Q+U)
* ``maxiter``: Maximum number of conjugate-gradient iterations for convergence
* ``query``: SQL-style query for observation selection
* ``tiled``: Enable tiled processing (``1``) or not (``0``)

**Resource Requirements:**

* Memory-intensive (typically 64–128 GB per process)
* Can benefit from multiple cores for linear algebra operations
* Disk I/O intensive for large datasets

Power Spectra
~~~~~~~~~~~~~

Power spectrum estimation workflow using PSpipe.

**Class:** :class:`~socm.workflows.spectra.SpectraWorkflow`

**Registered key:** ``"power-spectra"``

**Purpose:** Compute angular power spectra from maps produced by the mapmaking pipeline.

**Configuration Example:**

.. code-block:: toml

   [campaign.power-spectra]
   subcommand = "/path/to/script.py"
   script_args = ["file:///path/to/paramfile.dict"]
   script_flags = ["simulate-syst", "simulate-lens"]

**Key Parameters:**

* ``subcommand``: Path to the PSpipe Python script to run
* ``script_args``: Positional arguments passed to the script; ``file://`` URIs are resolved
* ``script_flags``: Boolean flags passed as ``--flag`` (list)

**Resource Requirements:**

* Scales with the number of map products being cross-correlated
* Some stages (e.g. mode-coupling matrix) are MPI-parallel and benefit from many ranks

SAT Simulation
~~~~~~~~~~~~~~

Small Aperture Telescope (SAT) simulation workflows for generating synthetic observations
using ``toast_so_sim``.

**Class:** :class:`~socm.workflows.sat_simulation.SATSimWorkflow`

**Registered key:** ``"sat-sims"``

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

ML Null Tests
~~~~~~~~~~~~~

Statistical tests to validate mapmaking results by creating maps from observation splits.

**Purpose:** Detect systematic errors and validate noise models by checking that null maps
(differences between splits) are consistent with noise.

All null tests share these common parameters (inherited from
:class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow`):

* ``chunk_nobs``: Number of observations per time chunk
* ``context``, ``area``, ``output_dir``, ``query``, ``preprocess_config``: same as ML Mapmaking

**Types of Null Tests:**

Mission Tests
^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.time_null_test.TimeNullTestWorkflow`

**Registered key:** ``"ml-null-tests.mission-tests"``

Splits observations in time to test for time-dependent systematics.

.. code-block:: toml

   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10
   nsplits = 8

Observations are sorted by timestamp, grouped into chunks of ``chunk_nobs``, and
distributed across ``nsplits`` splits in a time-interleaved fashion.

Wafer Tests
^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.wafer_null_test.WaferNullTestWorkflow`

**Registered key:** ``"ml-null-tests.wafer-tests"``

Splits observations by detector wafer to test for detector-dependent systematics.

.. code-block:: toml

   [campaign.ml-null-tests.wafer-tests]
   chunk_nobs = 10
   nsplits = 8

Observations are grouped by wafer slot; for each wafer, time-interleaved splits are
produced. One child workflow is created per (wafer, split) pair.

Direction Tests
^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.direction_null_test.DirectionNullTestWorkflow`

**Registered key:** ``"ml-null-tests.direction-tests"``

Splits observations by scan direction (rising, setting, or middle azimuth) to test for
scan-synchronous systematics. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.direction-tests]
   chunk_nobs = 10

Observations are classified by azimuth center into rising (az < 180°), setting (az > 180°),
or middle (az ≈ 180°) groups, and time-interleaved splits are created within each group.

PWV Tests
^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.pwv_null_test.PWVNullTestWorkflow`

**Registered key:** ``"ml-null-tests.pwv-tests"``

Splits observations by precipitable water vapour (PWV) level to test for
atmosphere-dependent systematics. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.pwv-tests]
   chunk_nobs = 10
   pwv_limit = 2.0

Observations above ``pwv_limit`` mm are classified as ``"high"``; the rest as ``"low"``.
Time-interleaved splits are created within each PWV group.

Day/Night Tests
^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.day_night_null_test.DayNightNullTestWorkflow`

**Registered key:** ``"ml-null-tests.day-night-tests"``

Splits observations into daytime and nighttime subsets to test for solar-related
systematics. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.day-night-tests]
   chunk_nobs = 10

Observations are classified using local sunrise/sunset times at the SO site
(San Pedro de Atacama, Chile).

Elevation Tests
^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.elevation_null_test.ElevationNullTestWorkflow`

**Registered key:** ``"ml-null-tests.elevation-tests"``

Splits observations by telescope elevation to test for elevation-dependent systematics
such as ground pickup or atmospheric gradients. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.elevation-tests]
   chunk_nobs = 10
   elevation_threshold = 45.0

Observations with elevation centre below ``elevation_threshold`` degrees are classified
as ``"low"``; the rest as ``"high"``.

Moon Rise/Set Tests
^^^^^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.moonrise_set_null_test.MoonRiseSetNullTestWorkflow`

**Registered key:** ``"ml-null-tests.moonrise-set-tests"``

Splits observations by whether the Moon is above the horizon during the observation,
to test for Moon-related contamination. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.moonrise-set-tests]
   chunk_nobs = 10

Observations are classified as ``"insky"`` (Moon above horizon) or ``"outsky"``
(Moon below horizon) using local moonrise/moonset times at the SO site.

Moon Close Tests
^^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.moon_close_null_test.MoonCloseFarNullTestWorkflow`

**Registered key:** ``"ml-null-tests.moon-close-tests"``

Splits observations by proximity to the Moon to test for near-field Moon sidelobe
contamination. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.moon-close-tests]
   chunk_nobs = 10
   sun_distance_threshold = 10.0

Observations whose angular separation from the Moon is within
``sun_distance_threshold`` + telescope field-of-view radius are classified as
``"close"``; the rest as ``"far"``.

Sun Close Tests
^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.sun_close_null_test.SunCloseFarNullTestWorkflow`

**Registered key:** ``"ml-null-tests.sun-close-tests"``

Splits observations by proximity to the Sun to test for near-field Sun sidelobe
contamination. Always uses ``nsplits = 2``.

.. code-block:: toml

   [campaign.ml-null-tests.sun-close-tests]
   chunk_nobs = 10
   sun_distance_threshold = 10.0

Observations are classified as ``"close"`` or ``"far"`` from the Sun using the same
angular-separation logic as the Moon Close test.

Smart Split Tests
^^^^^^^^^^^^^^^^^

**Class:** :class:`~socm.workflows.ml_null_tests.smart_split_null_test.SmartSplitNullTestWorkflow`

**Registered key:** ``"ml-null-tests.smart-split-tests"``

Ports the tenki/smartsplit algorithm for SO/sotodlib. Observations are grouped into
blocks (by day or by individual TOD), and a greedy hitmap-score algorithm with optional
relocation-based optimisation assigns blocks to balanced splits.

.. code-block:: toml

   [campaign.ml-null-tests.smart-split-tests]
   chunk_nobs = 10
   nsplits = 4
   block = "day"
   mode = "crosslink"
   nopt = 2000
   rad = 0.7
   res = 0.5

**Additional parameters (beyond the common null-test fields):**

* ``block``: Grouping mode — ``"day"`` (default) or ``"tod"``, optionally with a
  colon-separated multiplier, e.g. ``"day:2"`` for 2-day blocks.
* ``mode``: ``"plain"``, ``"crosslink"`` (default), or ``"scanpat"``.
  In crosslink mode rising and setting scans are balanced independently.
* ``nopt``: Number of block-relocate optimisation passes (default 2000).
* ``opt_mode``: ``"linear"`` (default) or ``"random"``.
* ``scanpat_tol``: Tolerance in degrees for grouping scan patterns (``mode="scanpat"``).
* ``constraint``: Path to a directory containing ``smart_split_N/query.txt`` files from
  a previous run; matching blocks are pre-assigned.
* ``rad``: Tophat smoothing radius in degrees applied to per-block hitmaps (default 0.7).
* ``res``: Sky-map pixel size in degrees (default 0.5).
* ``weight``: ``"plain"`` weights each scan by duration; ``"det"`` weights by n_samples.
* ``prefix``: Optional string prepended to virtual array names in the output.

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

   def get_command(self) -> str:
       """Return the command to execute."""
       return f"{self.executable} {self.subcommand}"

   def get_arguments(self) -> List[str]:
       """Return command arguments as a list of strings."""
       return [f"--param", self.custom_param, f"--threshold={self.threshold}"]

3. **Register the workflow:**

.. code-block:: python

   from socm.workflows import registered_workflows

   registered_workflows['my-custom'] = MyCustomWorkflow

Workflow Dependencies
---------------------

Workflows can depend on outputs from other workflows. The campaign manager handles:

* **Dependency resolution** - Ensures workflows run in the correct order
* **Resource optimization** - Schedules dependent workflows as early as possible using HEFT

Specify dependencies in the ``depends`` field using workflow names:

.. code-block:: toml

   [campaign.power-spectra]
   subcommand = "/path/to/spectra.py"
   depends = ["ml-mapmaking"]

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

See the :doc:`user_guide` for a full annotated example.

Best Practices
--------------

Resource Sizing
~~~~~~~~~~~~~~~

* **Memory:** Allocate 20–50% more than estimated need
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
