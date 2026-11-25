Workflows
=========

A workflow is one task SO Campaign Manager runs: a command, its options and its
resources. This page lists every workflow type and its options. Which ones a campaign
can use depends on its type:

* **Mapmaking** (``socm lat-mapmaking``): `ML Mapmaking`_, `ML Null Tests`_ and
  `SAT Simulation`_, one TOML table each.
* **Power spectra** (``socm spectra``): `Power Spectra`_ stages.
* **LAT simulations** (``socm lat-sims``): ``get-schedule``, ``shell-script``,
  ``lat-sims`` and ``sat-sims`` stages, see `LAT Simulations`_.

:doc:`campaigns` shows a complete campaign of each type. To add a workflow type, see
:doc:`advanced_topics`.

Workflow Types
--------------

ML Mapmaking
~~~~~~~~~~~~

Makes maximum likelihood maps from time-ordered data with ``so-site-pipeline
make-ml-map``. Runs in a mapmaking campaign.

**Class:** :class:`~socm.workflows.ml_mapmaking.MLMapmakingWorkflow`

**Registered key:** ``"ml-mapmaking"``

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

**Parameters:**

* ``context`` (required): sotodlib context file (``file://`` URI)
* ``area`` (required): FITS file defining the sky area to map (``file://`` URI)
* ``preprocess_config`` (required): preprocessing configuration (``file://`` URI)
* ``output_dir`` (required): directory for the maps
* ``query``: observation database query, or a ``file://`` list of observation IDs
  (default: all observations)
* ``bands``, ``wafers``: frequency bands and wafers to map
* ``comps``: map components (default ``"TQU"``)
* ``maxiter``, ``downsample``: iterations and downsampling factor per pass, e.g.
  ``"200,200"`` and ``"4,2"`` (defaults 500 and 1)
* ``tiled``: tiled maps, ``1`` (default) or ``0``
* ``site``: observatory site (default ``"so_lat"``)

The context is opened when the campaign is built, to size the workflow from the number
of samples it will read.

Power Spectra
~~~~~~~~~~~~~

Computes angular power spectra from maps with PSpipe. Each stage of a power spectra
campaign is one of these workflows, running one PSpipe script.

**Class:** :class:`~socm.workflows.spectra.SpectraWorkflow`

**Configuration Example:**

.. code-block:: yaml

   stages:
     get_spectra_from_maps:
       executable: python -u
       script: /path/to/PSpipe/project/SO/pISO/python/get_spectra_from_maps.py
       script-args: [file:///path/to/paramfile.dict]
       script-kwargs: {start: 0, stop: 10}
       script-flags: [simulate-syst, simulate-lens]
       depends: [get_pseudo2datavec]
       resources: {memory: 600G, ranks: 17, threads: 4, runtime: 15m}

**Key Parameters:**

* ``script``: Path to the PSpipe Python script to run
* ``script-args``: Positional arguments passed to the script. Only ``file://`` values
  are passed on, resolved to absolute paths.
* ``script-kwargs``: Options passed as ``--key=value`` (mapping)
* ``script-flags``: Boolean flags passed as ``--flag`` (list)

See :doc:`campaigns` for a complete power spectra campaign.

SAT Simulation
~~~~~~~~~~~~~~

Simulates Small Aperture Telescope (SAT) observations with ``toast_so_sim``.

**Class:** :class:`~socm.workflows.sat_simulation.SATSimWorkflow`

**Registered key:** ``"sat-sims"``

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
* ``sim_noise``, ``scan_map``, ``sim_atmosphere``, ``sim_sss``, ``sim_hwpss``: turn the
  noise, map scanning, atmosphere, spin-synchronous and HWP-synchronous signal
  operators on (``true``) or off (``false``, the default)
* ``pixels_healpix_radec_nside``: HEALPix resolution (default: 512)

A SAT simulation runs either as a ``[campaign.sat-sims]`` table in a mapmaking campaign
(``socm lat-mapmaking``), or as a stage with ``type: sat-sims`` in a LAT simulations
campaign (``socm lat-sims``), where it can depend on other stages and use a matrix.

LAT Simulations
~~~~~~~~~~~~~~~

A LAT simulations campaign (``socm lat-sims -y campaign.yml``) is a DAG of stages
that typically generates an observing schedule, splits it, and runs ``toast_so_sim``
for every split, band, tube and signal component. Each signal run waits for the noise
run whose noise matrices it loads.

**Workflow types** (selected with a stage's ``type``; the stage name is used when
``type`` is not given):

* ``get-schedule``: runs ``toast_ground_schedule``. Its options usually come from a
  par file; ``output_dir`` is passed as ``--out``.
* ``shell-script``: runs ``bash <script> <script-args...>``. Use it for steps that have
  no workflow class of their own, such as splitting the schedule. Only ``bash`` is
  needed on the compute node.
* ``lat-sims``: runs ``toast_so_sim``. Typed fields are ``output_dir`` (``--out``),
  ``config``, ``schedule``, ``sort_schedule``, ``bands``, ``tube_slots``,
  ``sample_rate`` and ``job_group_size`` (default 1). Every other key is passed
  through as a toast option.
* ``sat-sims``: runs ``toast_so_sim`` for a SAT, see `SAT Simulation`_.

**Stage keys** read by socm itself:

* ``type``: the workflow type, see above.
* ``param-file``: an argparse ``@file``, one argument per line. Relative paths are
  resolved against the YAML file's directory.
* ``base-path``: the directory the task sandboxes are created in; defaults to the
  campaign's ``base-path``, otherwise RADICAL-Pilot's own sandbox.
* ``depends``: names of the stages this stage waits for.
* ``resources``: ``memory``, ``ranks``, ``threads`` and ``runtime``. ``ranks`` is the
  total number of MPI ranks, e.g. 272 for 17 nodes with 16 ranks of 7 threads each.
* ``matrix``: expands the stage into several workflows, see below.

**Configuration Example:**

.. code-block:: yaml

   campaign:
     deadline: 48h
     resource: tiger3
     execution_schema: remote
     requested_resources: 1904

   stages:
     get-schedule:
       param-file: ./schedule_param.par
       output_dir: /scratch/lat/schedules/schedule_lat.txt
       resources: {memory: 48G, ranks: 1, threads: 8, runtime: 10m}

     split-schedule:
       type: shell-script
       script: ./scripts/split_schedule_months.sh
       script-args: [/scratch/lat/schedules/schedule_lat.txt, /scratch/lat/split, "4", "10"]
       depends: [get-schedule]
       resources: {memory: 1G, ranks: 1, threads: 1, runtime: 5m}

     lat-noise:
       type: lat-sims
       matrix:
         split: [1, 2, 3, 4]
         tube: [i6, i1, i3, i4]
         band:
           - {band: LAT_f090, alpha: "2.654"}
           - {band: LAT_f150, alpha: "2.744"}
       executable: /path/to/env/bin/toast_so_sim
       config: /path/to/mss-0003_lat.yaml
       schedule: /scratch/lat/split/schedule.${split}.txt
       sort_schedule: true
       bands: ${band}
       tube_slots: ${tube}
       output_dir: /scratch/lat/out/${band}/${tube}/split_${split}/noise
       operators:
         sim_noise: true
         common_mode_noise: {enable: true, alpha: "${alpha}", NET: 'Quantity("0.0004304 K s(1/2)")'}
         mlmapmaker: {nmat_dir: "/scratch/lat/out/${band}/${tube}/split_${split}/noise/nmats", nmat_mode: cache}
       depends: [split-schedule]
       resources: {memory: 8000G, ranks: 272, threads: 7, runtime: 40h}

     lat-signal:
       type: lat-sims
       matrix:
         split: [1, 2, 3, 4]
         tube: [i6, i1, i3, i4]
         band: [LAT_f090, LAT_f150]
         comp: [cmb, foreground]
       param-file: ./signal.par
       schedule: /scratch/lat/split/schedule.${split}.txt
       bands: ${band}
       tube_slots: ${tube}
       output_dir: /scratch/lat/out/${band}/${tube}/split_${split}/${comp}
       scan_alm.file: /scratch/lat/input_maps/${comp}_alm_${band}_{wafer_slot}.healpix.fits
       mlmapmaker.nmat_dir: /scratch/lat/out/${band}/${tube}/split_${split}/noise/nmats
       depends: [lat-noise]   # each run waits for the noise run of its own split, tube and band
       resources: {memory: 8000G, ranks: 34, threads: 56, runtime: 45h}

Paths shared between stages should be absolute: every task runs in its own sandbox.

**Toast options.** A ``lat-sims`` option can be given in three equivalent forms, and
all three produce the same command line:

* in a par file: ``--sim_noise.enable``, ``--mlmapmaker.nmat_mode=load``;
* as flat keys under its command-line name: ``sim_noise: true``,
  ``mlmapmaker.nmat_mode: load``;
* in an ``operators`` mapping: ``operators: {sim_noise: true, mlmapmaker: {nmat_mode: load}}``.

They are written out as follows:

* An operator name set to a boolean (``sim_noise: true``, or ``enable:`` inside
  ``operators``) becomes ``--op.enable`` or ``--op.disable``.
* A boolean trait (``mlmapmaker.deslope: false``) becomes toast's ``--op.trait`` or
  ``--op.no_trait``. Toast only defines the flag that changes the trait's default, so
  set a boolean trait only to the opposite of its default.
* Any other value becomes ``--op.trait=value``. Values containing spaces or quotes,
  such as ``Quantity("0.0004 K s(1/2)")``, need no extra shell quoting.
* A list, e.g. an option repeated in a par file, becomes one argument per item.
* ``sort_schedule`` is a plain flag, written only when true.

**Precedence:**

* The stage overrides its par file, whatever form either uses: a stage
  ``output_dir`` beats ``--out`` in the par file, and stage ``operators`` beat flat
  options in the par file.
* Within one source, flat keys beat ``operators``.
* Within a par file, the last occurrence of an option wins. This includes
  ``--op.trait`` against ``--op.no_trait``. For a typed field, such as
  ``sample_rate``, the last value is kept even across ``@include`` files.

Stage Matrices
^^^^^^^^^^^^^^

A ``matrix`` expands one stage into a workflow per combination of its values. It
works for every workflow type.

* **Axes:** the matrix maps axis names to lists, and the workflows are their cartesian
  product, in key order. They are named ``<stage>.<v1>.<v2>...``, e.g.
  ``lat-noise.1.i6.LAT_f090``. An empty or ``null`` matrix means no matrix.
* **Placeholders:** ``${axis}`` (or ``$axis``) is replaced in every string of the
  stage, nested ``operators`` and the ``param-file`` path included, but not in
  ``type`` and ``depends``. Unknown names, such as ``$SCRATCH``, are left as they are,
  and so is toast's own ``{wafer_slot}`` placeholder. Placeholders are not filled in
  inside par files, so values that change per workflow belong in the stage.
* **Mapping rows:** a row can be a mapping, such as ``{band: LAT_f090, alpha: "2.654"}``.
  All of its keys become variables, and it must set the axis's own key.
* **Booleans:** when a placeholder is the whole value of an option (a toast option,
  an ``operators`` entry or a ``script-kwargs`` entry), a boolean axis value stays a
  boolean: ``sim_noise: ${noise}`` gives ``--sim_noise.enable`` or
  ``--sim_noise.disable``, and ``equalize-time: ${equalize}`` gives ``--equalize-time``
  or nothing. In the workflow's declared fields, such as ``script-args`` and
  ``environment``, and inside longer strings, it is inserted as text (``True``).
* **Dependencies:** ``depends: [parent]`` links each workflow to the workflows of the
  parent stage that have the same values on the axes the two stages share. In the
  example, each ``lat-signal`` run waits only for its own ``lat-noise`` run, and every
  ``lat-noise`` run waits for ``split-schedule``. A stage that shares no axes with its
  parent waits for all of the parent's workflows. A workflow with no matching parent
  is an error.

ML Null Tests
~~~~~~~~~~~~~

Null tests split the observations in two or more groups and make an ML map of each,
to check that the differences between them are consistent with noise. Each test table
creates one workflow per split. They run in a mapmaking campaign; keys set in
``[campaign.ml-null-tests]`` apply to, and override, every test table under it.

All null tests take the ML Mapmaking parameters (``context``, ``area``,
``preprocess_config``, ``output_dir``, ``query``, ...) and:

* ``chunk_nobs``: number of observations per chunk; chunks are dealt to the splits in
  turn, so every split spans the whole period
* ``nsplits``: number of splits (default 8 for mission and wafer tests, 4 for smart
  split tests, 2 for the others). Tests that first group observations, e.g. by scan
  direction, make ``nsplits`` splits within each group.

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
scan-synchronous systematics. Uses ``nsplits = 2`` by default.

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
atmosphere-dependent systematics. Uses ``nsplits = 2`` by default.

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
systematics. Uses ``nsplits = 2`` by default.

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
such as ground pickup or atmospheric gradients. Uses ``nsplits = 2`` by default.

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
to test for Moon-related contamination. Uses ``nsplits = 2`` by default.

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
contamination. Uses ``nsplits = 2`` by default.

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
contamination. Uses ``nsplits = 2`` by default.

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

Workflow Dependencies
---------------------

Dependencies exist only in the YAML campaigns: each stage lists the stages it waits for
under ``depends``, and a stage starts only once all of them are done. If one fails, the
stage is never started. In a ``lat-sims`` campaign, a matrix stage's workflows wait only
for the parent workflows with the same values on the shared axes (see
`Stage Matrices`_).

Mapmaking campaigns (TOML) have no dependencies: their workflows may run in any order,
and subcampaigns such as ``ml-null-tests`` only share configuration.
