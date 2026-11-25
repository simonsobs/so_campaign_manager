FAQ and Troubleshooting
=======================

General
-------

**What is the difference between a workflow and a campaign?**
   A workflow is one task, e.g. one map or one simulation. A campaign is the set of
   workflows socm plans together to finish within a deadline.

**Which campaign types are there?**
   Mapmaking (``socm lat-mapmaking``, TOML), power spectra (``socm spectra``, YAML) and
   LAT simulations (``socm lat-sims``, YAML). See :doc:`campaigns`.

**Which clusters are supported?**
   Tiger 3 (``tiger3``, the default), Perlmutter (``perlmutter``), Universe
   (``universe``) and the local machine (``localhost``). Other SLURM clusters need a
   resource class; see :doc:`resources`.

**Can I test a campaign without running it?**
   Yes: add ``--dry-run``. socm builds the workflows and plans them, but submits
   nothing. To run small tests on the machine you are on, use ``resource = "localhost"``.

Configuration
-------------

**How do I write durations and sizes?**
   ``deadline`` and ``runtime`` take durations such as ``"30m"``, ``"2h"``, ``"3d"`` or
   ``"1w"``; ``memory`` takes sizes such as ``"80G"``. A bare number is seconds for a
   duration and bytes for a size, so ``memory = "80000"`` is 80 kB.

**Why ``file://`` paths?**
   A ``file://`` value marks a file: socm reads a ``file://`` ``query`` as a list of
   observation IDs, and turns other ``file://`` values, such as ``script-args``, into
   absolute paths. For ``socm spectra`` ``script-args``, only ``file://`` values are
   passed on at all.

**How do I share settings between workflows?**
   In TOML, put them in a subcampaign table such as ``[campaign.ml-null-tests]``; they
   apply to every test under it. In YAML, use anchors (``&name`` and ``*name``) or a
   stage ``matrix``.

**Can the configuration read environment variables?**
   No; values are used as written. Use the ``environment`` table to set variables for
   a task.

**Why does my YAML stage fail to parse?**
   In flow style (``{...}``), a ``${...}`` placeholder must be quoted:
   ``mlmapmaker: {nmat_dir: "/out/${band}"}``.

Scheduling
----------

**How is the QoS chosen?**
   With ``execution_schema = "remote"``, the planner finds the fewest cores, up to
   ``requested_resources``, that meet the deadline, then picks one QoS tier for the
   campaign. If no tier allows the whole deadline, the campaign is split into
   several pilot jobs that run one after another. See :doc:`resources`.

**What does "Cannot meet ... deadline with ... cores" mean?**
   No plan with at most ``requested_resources`` cores finishes within the deadline.
   Increase either, or check that the workflows' ``runtime`` values are realistic.

**What if a workflow runs longer than its ``runtime``?**
   Each pilot job's walltime is its planned duration plus 25%, capped by the QoS. A
   workflow that runs well past its estimate can hit that limit, and then fails.

**How do I choose ranks, threads and memory?**
   Measure a small run (``sacct -j <pilot_job_id> --format=JobID,Elapsed,MaxRSS``),
   then scale. socm records every successful workflow in Slurmise for future
   predictions.

Running
-------

**How do I follow a campaign?**
   Run with ``SOCM_LOG_LEVEL=INFO``, read the logs in ``./socm.session.*/``, and use
   ``squeue -u $USER``: it lists the pilot jobs, and the workflows run inside them.

**Where is a workflow's output?**
   In its ``output_dir``, if it has one. Its ``stdout`` and ``stderr`` are
   ``workflow.<id>.out`` and ``.err`` in its sandbox, which is
   ``<base-path>/<workflow name>.<id>`` in YAML campaigns with a ``base-path``.

**How do I stop a campaign?**
   Press Ctrl+C. socm shuts down its pilot jobs on the way out; check ``squeue`` and
   ``scancel`` any that remain.

**Can I resume a failed campaign?**
   Not automatically. Remove the workflows that finished from the configuration (in
   YAML, also from other stages' ``depends``) and run it again.

Errors
------

**A workflow failed. What happened to the rest?**
   Its dependents never start, the campaign ends as ``FAILED``, and socm stops the
   workflows still running. Read the failed task's ``.err`` file first.

**"command not found" on the compute node**
   The executable is not on the node's ``PATH``. Give its full path (``executable``),
   or set ``PATH`` in the workflow's ``environment``.

**socm lat-mapmaking ignores my ML mapmaking or null-test tables**
   Without the ``mapmaking`` extra (``sotodlib`` and ``astral``) these workflow types
   are not available, and their tables are skipped. Install the extra. These workflows
   also open the context when they are created, so run socm where the context is
   reachable.

**"Stage 'x': unknown workflow type 'y'"**
   The stage's ``type``, or its name when there is no ``type``, is not a registered
   workflow; the message lists the known ones.

**"Stage 'x' depends on unknown stage 'y'"**
   A ``depends`` entry does not name a stage in the file.

**"Workflow 'x' matches no workflow of stage 'y'"**
   A matrix stage depends on a matrix stage that has no workflow with the same values
   on their shared axes. Check that the shared axes list the same values.

**toast reports an unrecognized argument such as ``--op.no_trait``**
   Toast only defines the flag that changes a boolean trait's default. Set a boolean
   trait only to the opposite of its default.

Getting Help
------------

Report bugs and feature requests at
https://github.com/simonsobs/so_campaign_manager/issues, with the configuration, the
error and the socm version. Contact your HPC center for SLURM or system problems.

Glossary
--------

**Campaign**
   The set of workflows socm plans and runs together.
**Workflow**
   One task: a command, its options and its resources.
**Stage**
   A YAML entry that creates one workflow, or one per combination of its ``matrix``.
**Pilot job**
   The SLURM job RADICAL-Pilot submits; workflows run inside it as job steps.
**QoS**
   A SLURM Quality of Service tier, with walltime and core limits.
**HEFT**
   Heterogeneous Earliest Finish Time, the scheduling algorithm the planner uses.
**Bookkeeper, Planner, Enactor**
   socm's orchestrator, scheduler and execution backend; see :doc:`architecture`.
