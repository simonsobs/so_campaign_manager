User Guide
==========

This page covers running and operating campaigns. :doc:`campaigns` shows how to write
each type of campaign, and :doc:`workflows` lists the options of every workflow.

Command Line Interface
----------------------

Each campaign type has its own subcommand:

.. code-block:: bash

   socm lat-mapmaking -t campaign.toml   # ML mapmaking and null tests
   socm spectra -y campaign.yml          # PSpipe power spectra
   socm lat-sims -y campaign.yml         # LAT simulations

Options:

* ``-t, --toml``: the TOML configuration (``lat-mapmaking``, required)
* ``-y, --yaml``: the YAML configuration (``spectra`` and ``lat-sims``, required)
* ``--dry-run``: plan the campaign and simulate its execution without submitting
  anything to SLURM

``socm`` then:

1. reads the configuration and creates the workflows;
2. plans them with HEFT to fit the ``deadline``, picking the core count and QoS;
3. submits them to SLURM through RADICAL-Pilot, each workflow once its dependencies
   are done;
4. returns when every workflow has finished, or when one has failed.

Keep ``socm`` running for the whole campaign, e.g. in ``tmux`` or ``screen`` on the
login node.

Environment Variables for Tasks
-------------------------------

A workflow's ``environment`` mapping is set in its task's environment:

.. code-block:: toml

   [campaign.ml-mapmaking.environment]
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

In a ``lat-sims`` campaign, add ``environment:`` to a stage. ``socm spectra`` does not
pass ``environment`` on.

Logs
----

Each component (bookkeeper, planner, enactor) writes its own log file in the session
directory, which is created in the directory ``socm`` is started from. The terminal
shows only warnings and errors; set ``SOCM_LOG_LEVEL`` to ``INFO`` or ``DEBUG`` to see
more:

.. code-block:: bash

   SOCM_LOG_LEVEL=INFO socm lat-sims -y campaign.yml

Each task writes ``workflow.<id>.out`` and ``workflow.<id>.err`` in its sandbox. In
power spectra and LAT simulations campaigns with a ``base-path``, the sandbox is
``<base-path>/<workflow name>.<id>``; otherwise it is in RADICAL-Pilot's session
sandbox. All tasks of a campaign run inside its pilot jobs, so ``squeue`` shows the
pilot jobs, not the individual workflows.

Resource Predictions
--------------------

After each successful workflow, its runtime and memory are recorded in Slurmise for
future resource predictions. The Slurmise database is in ``$SOCM_SLURMISE_DIR`` if
set, otherwise ``<base-path>/slurmise_dir``, otherwise ``./slurmise_dir``. Failed
workflows are not recorded.

When a Workflow Fails
---------------------

A workflow fails when its task ends as failed or canceled, for example because its
command exits with a non-zero status. Then:

* the workflows that depend on it are never started;
* the campaign ends as ``FAILED`` and socm shuts down: workflows that are still
  running are stopped and no further pilot jobs are submitted.

To recover, fix the cause and run the campaign again. To skip work that already
finished, remove those workflows from the configuration first; in a YAML campaign,
also remove them from the ``depends`` lists of other stages.

Scheduling Policy
-----------------

``policy = "time"``, the default and only policy, minimizes the campaign's completion
time. The planner orders workflows with HEFT (Heterogeneous Earliest Finish Time).
With ``execution_schema = "remote"`` it also searches for the smallest core count that
still meets the deadline; with ``"batch"`` it uses ``requested_resources`` cores.

Troubleshooting
---------------

**The configuration is rejected**
   Check the TOML or YAML syntax and the required keys, and run with ``--dry-run``.
   In YAML flow style (``{...}``), quote values that contain ``${...}`` placeholders.

**The deadline cannot be met**
   The planner found no core count up to ``requested_resources`` that finishes in
   time. Increase ``deadline`` or ``requested_resources``, or lower the workflows'
   ``runtime``.

**A workflow runs out of memory or time**
   Increase its ``memory`` or ``runtime``. Remember that a bare number is bytes for
   ``memory`` and seconds for ``runtime``.

**A workflow fails at once**
   Check its output and error files in the sandbox: usually a wrong path, a missing
   ``environment`` variable or a missing executable on the compute node. Paths shared
   between stages must be absolute.
