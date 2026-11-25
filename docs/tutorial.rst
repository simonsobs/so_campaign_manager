Tutorial
========

This tutorial builds two campaigns step by step: an ML mapmaking campaign with null
tests, and a LAT simulation pipeline. It then shows how to follow a running campaign,
recover from a failure and size resources. :doc:`campaigns` has the finished
examples, including a power spectra campaign.

Before you start you need SO Campaign Manager installed with the ``mapmaking`` extra
(see :doc:`installation`), an account on a SLURM cluster such as Tiger 3, and a
sotodlib context for the data you want to map.

Tutorial 1: Your First Campaign
-------------------------------

Step 1: Write the Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``my_first_campaign.toml`` with one ML mapmaking workflow:

.. code-block:: toml

   [campaign]
   deadline = "4h"                # the whole campaign must finish within 4 hours
   resource = "tiger3"
   execution_schema = "remote"    # let the planner choose the cores and QoS
   requested_resources = 448      # ...using at most 448 cores

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   preprocess_config = "file:///path/to/preprocess.yaml"
   output_dir = "/path/to/output"
   query = "obs_id='your_observation_id'"
   bands = "f090"
   maxiter = 100

   [campaign.ml-mapmaking.resources]
   ranks = 1
   threads = 32
   memory = "80G"     # a size with a unit; a bare number is bytes
   runtime = "2h"     # a duration; a bare number is seconds

   [campaign.ml-mapmaking.environment]
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

File parameters (``context``, ``area``, ``preprocess_config``, a ``query`` file) are
``file://`` URIs; write them as absolute paths. The ``environment`` table is set in
the task's environment on the compute node.

Step 2: Check It with a Dry Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   socm lat-mapmaking -t my_first_campaign.toml --dry-run

A dry run reads the configuration, creates the workflows and plans them, but submits
nothing. ML mapmaking opens the context while the workflow is created, so a wrong
path or an unreachable database shows up here. If the deadline cannot be met with
``requested_resources`` cores, planning fails and says so.

Step 3: Run It
~~~~~~~~~~~~~~

.. code-block:: bash

   SOCM_LOG_LEVEL=INFO socm lat-mapmaking -t my_first_campaign.toml

``socm`` stays in the foreground until the campaign ends, so start it in ``tmux`` or
``screen``. Without ``SOCM_LOG_LEVEL`` the terminal shows only warnings and errors.

While it runs:

* ``squeue -u $USER`` shows the pilot job socm submitted; the workflows run inside it.
* The socm logs are in ``./socm.session.*/`` in the directory you started from.
* The maps appear in ``output_dir``.

Tutorial 2: Add Null Tests
--------------------------

Null tests split the observations and map each split. Add them to the same file:

.. code-block:: toml

   # Settings shared by every null test
   [campaign.ml-null-tests]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   preprocess_config = "file:///path/to/preprocess.yaml"
   output_dir = "/path/to/output/null_tests"
   query = "file:///path/to/obs_ids.txt"    # one observation ID per line
   bands = "f090"
   maxiter = "100,100"     # two passes...
   downsample = "4,2"      # ...downsampled by 4, then by 2

   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10         # observations per chunk, dealt to the splits in turn
   nsplits = 4

   [campaign.ml-null-tests.mission-tests.resources]
   ranks = 35
   threads = 8
   memory = "2400G"
   runtime = "4h"

   [campaign.ml-null-tests.direction-tests]
   chunk_nobs = 10

   [campaign.ml-null-tests.direction-tests.resources]
   ranks = 17
   threads = 8
   memory = "80G"
   runtime = "4h"

The keys in ``[campaign.ml-null-tests]`` apply to every test under it. Each test
creates one workflow per split: the mission tests above give four workflows, and the
direction tests two per scan direction. Each split's observation list is written to
its own directory under ``output_dir``.

All workflows of a mapmaking campaign are independent, so the planner runs them side
by side as cores allow. See :doc:`workflows` for the other null tests.

Tutorial 3: A LAT Simulation Pipeline
-------------------------------------

A LAT simulation campaign is a YAML file of stages that depend on each other. This
one generates a schedule, splits it, simulates noise for each split and band, and
then simulates the CMB on top of each noise run.

Step 1: Generate the Schedule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Put the ``toast_ground_schedule`` options in ``schedule.par``, one argument per line:

.. code-block:: text

   --site-name
   ATACAMA
   --telescope
   LAT
   --start
   2025-01-01 00:00:00
   --stop
   2026-01-01 00:00:00
   --patch
   RISING_SCAN_40,HORIZONTAL,1.00,30.00,150.00,40.00,1440

and start ``lat_campaign.yml`` with a ``get-schedule`` stage:

.. code-block:: yaml

   campaign:
     deadline: 48h
     resource: tiger3
     execution_schema: remote
     requested_resources: 3808
     base-path: /scratch/lat/sandboxes

   stages:
     get-schedule:
       param-file: ./schedule.par
       output_dir: /scratch/lat/schedule.txt
       resources: {memory: 48G, ranks: 1, threads: 8, runtime: 10m}

The stage name is also its type. Its ``output_dir`` is passed as ``--out``.

Step 2: Split It with a Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Steps without a workflow class of their own run as ``shell-script`` stages. The
script runs with ``bash`` and gets ``script-args`` as its arguments:

.. code-block:: yaml

     split-schedule:
       type: shell-script
       script: ./scripts/split_schedule.sh
       script-args: [/scratch/lat/schedule.txt, /scratch/lat/split, "2"]
       depends: [get-schedule]
       resources: {memory: 1G, ranks: 1, threads: 1, runtime: 5m}

Relative ``param-file`` and ``script`` paths are resolved against the YAML file's
directory. Paths shared between stages, like the schedule, must be absolute: every
task runs in its own sandbox.

Step 3: Simulate Noise with a Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``matrix`` turns one stage into one workflow per combination of its values, and
``${name}`` placeholders take each combination's values:

.. code-block:: yaml

     lat-noise:
       type: lat-sims
       matrix:
         split: [1, 2]
         band: [LAT_f090, LAT_f150]
       config: /path/to/lat_sim_config.yaml
       schedule: /scratch/lat/split/schedule.${split}.txt
       bands: ${band}
       tube_slots: i6
       output_dir: /scratch/lat/out/${band}/split_${split}/noise
       operators:
         sim_noise: true
         mlmapmaker:
           nmat_dir: /scratch/lat/out/${band}/split_${split}/noise/nmats
           nmat_mode: cache
       depends: [split-schedule]
       resources: {memory: 8000G, ranks: 272, threads: 7, runtime: 40h}

This gives four workflows, ``lat-noise.1.LAT_f090`` to ``lat-noise.2.LAT_f150``.
``sim_noise: true`` becomes ``--sim_noise.enable``, and ``mlmapmaker``'s traits
become ``--mlmapmaker.nmat_dir=...`` and ``--mlmapmaker.nmat_mode=cache``.

Step 4: Simulate the Signal on Each Noise Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

     lat-cmb:
       type: lat-sims
       matrix:
         split: [1, 2]
         band: [LAT_f090, LAT_f150]
       config: /path/to/lat_sim_config.yaml
       schedule: /scratch/lat/split/schedule.${split}.txt
       bands: ${band}
       tube_slots: i6
       output_dir: /scratch/lat/out/${band}/split_${split}/cmb
       scan_alm: true
       scan_alm.file: /scratch/lat/input/cmb_alm_${band}_{wafer_slot}.fits
       mlmapmaker.nmat_dir: /scratch/lat/out/${band}/split_${split}/noise/nmats
       mlmapmaker.nmat_mode: load
       depends: [lat-noise]
       resources: {memory: 8000G, ranks: 34, threads: 56, runtime: 45h}

Because both stages have the ``split`` and ``band`` axes, each ``lat-cmb`` workflow
waits only for the ``lat-noise`` workflow with the same split and band, the one whose
noise matrices it loads. ``{wafer_slot}`` is not a matrix placeholder; it reaches
toast unchanged.

Options can be written flat, as here, or under ``operators``, as in ``lat-noise``.
They can also come from a ``param-file``; the stage's own settings override it.

Step 5: Run It
~~~~~~~~~~~~~~

.. code-block:: bash

   socm lat-sims -y lat_campaign.yml --dry-run
   socm lat-sims -y lat_campaign.yml

Each task's sandbox is ``/scratch/lat/sandboxes/<workflow name>.<id>``, with its
output in ``workflow.<id>.out`` and ``workflow.<id>.err``. :doc:`workflows` covers
every stage key and matrix rule.

Tutorial 4: When a Workflow Fails
---------------------------------

If a task fails, for example because its command exits with an error:

* the workflows that depend on it never start;
* the campaign ends as ``FAILED``, and socm stops the workflows still running and
  exits.

To find the cause, read the failed task's ``.err`` file in its sandbox, and the socm
logs in ``./socm.session.*/``. Fix the problem, remove the workflows that already
finished from the configuration (in YAML, also from other stages' ``depends``), and
run the campaign again.

Tutorial 5: Sizing Resources
----------------------------

The planner fits the campaign into the deadline using each workflow's ``ranks``,
``threads``, ``memory`` and ``runtime``, so better estimates give better plans.

1. Run a small version first: a few observations, or one matrix value per axis, with
   a short ``deadline``.
2. Measure it:

   .. code-block:: bash

      sacct -j <pilot_job_id> --format=JobID,JobName,Elapsed,MaxRSS

   Each workflow is a job step of the pilot job.
3. Set ``memory`` and ``runtime`` from the measurements, with a margin, and scale them
   with the amount of data.

socm also records the runtime and memory of every successful workflow in Slurmise for
future predictions (see :doc:`user_guide`).

Next Steps
----------

* :doc:`campaigns`: complete examples of every campaign type
* :doc:`workflows`: every workflow and stage option
* :doc:`user_guide`: logs, failures and troubleshooting
* :doc:`resources`: the supported clusters and their QoS tiers
