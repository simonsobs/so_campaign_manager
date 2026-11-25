Advanced Topics
===============

This page is for developers who extend SO Campaign Manager. :doc:`architecture`
describes how the components fit together, and :doc:`developer_guide` covers the
development setup.

Custom Workflows
----------------

A workflow class describes one kind of task: its options as Pydantic fields, and the
command they produce.

**Step 1: Define the Workflow Class**

Create a new Python file in ``src/socm/workflows/``:

.. code-block:: python

   # src/socm/workflows/my_custom_workflow.py
   import shlex
   from typing import Any

   from socm.core.models import Workflow

   class MyCustomWorkflow(Workflow):
       """Custom workflow for a specific analysis task."""

       name: str = "my_custom_workflow"
       executable: str = "my-tool"
       custom_param1: str
       custom_param2: str | None = None
       threshold: float = 0.5

       def get_arguments(self, **kargs: Any) -> list[str]:
           """One list entry per argument, unquoted. RADICAL-Pilot runs
           ``executable`` with these arguments; a single string would be split
           into characters."""
           args = [f"--param1={self.custom_param1}", f"--threshold={self.threshold}"]
           if self.custom_param2:
               args.append(f"--param2={self.custom_param2}")
           return args

       def get_command(self, **kargs: Any) -> str:
           """The full command as a shell string, for logs and Slurmise."""
           return shlex.join([self.executable, *self.get_arguments()])

       @classmethod
       def get_workflows(cls, descriptions: list[dict] | dict) -> list["MyCustomWorkflow"]:
           """Create workflow instances from configuration descriptions."""
           if isinstance(descriptions, dict):
               descriptions = [descriptions]
           return [cls(**desc) for desc in descriptions]

**Step 2: Register the Workflow**

Add it to ``registered_workflows`` in ``src/socm/workflows/__init__.py``:

.. code-block:: python

   from .my_custom_workflow import MyCustomWorkflow

   registered_workflows = {
       # ... existing workflows
       "my-custom-workflow": MyCustomWorkflow,
   }

A registered workflow can then be used as a table in a mapmaking campaign, or as a
stage type in a LAT simulations campaign, where it gets ``depends``, ``matrix`` and
``param-file`` support:

.. code-block:: toml

   [campaign.my-custom-workflow]
   custom_param1 = "value1"
   threshold = 0.75

   [campaign.my-custom-workflow.resources]
   ranks = 16
   threads = 4
   memory = "64G"
   runtime = "2h"

.. code-block:: yaml

   stages:
     my-stage:
       type: my-custom-workflow
       custom_param1: value1
       resources: {memory: 64G, ranks: 16, threads: 4, runtime: 2h}

To group workflows under a subcampaign table such as ``[campaign.ml-null-tests]``, add
them to ``subcampaign_map`` in the same file.

**Step 3: Normalize Option Names (optional)**

If options can arrive under names other than your field names, for example a par
file's ``--out`` for ``output_dir``, override ``normalize_options``. ``build_dag``
calls it on each source (par file, stage) before merging them, so the stage wins
whatever name either uses. It must be idempotent:

.. code-block:: python

   @classmethod
   def normalize_options(cls, options: dict) -> dict:
       options = dict(options)
       if "out" in options:
           options["output_dir"] = options.pop("out")
       return options

Call it from a ``model_validator(mode="before")`` too, so that constructing the class
directly behaves the same; see ``GetScheduleWorkflow``.

**Step 4: Add Tests**

Test the arguments and the command in ``tests/workflows/test_my_custom_workflow.py``:

.. code-block:: python

   from socm.workflows.my_custom_workflow import MyCustomWorkflow

   def test_get_arguments_is_a_list():
       workflow = MyCustomWorkflow(custom_param1="a b", threshold=0.9)
       assert workflow.get_arguments() == ["--param1=a b", "--threshold=0.9"]

   def test_get_command_quotes_for_the_shell():
       workflow = MyCustomWorkflow(custom_param1="a b")
       assert workflow.get_command() == "my-tool '--param1=a b' --threshold=0.5"

Fields Recorded in Slurmise
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a workflow succeeds, its ``get_numeric_fields()`` are recorded in Slurmise as
numerical features and its ``get_categorical_fields()`` as categorical ones. Both are
derived from the workflow's fields; override them to leave fields out or add
derived ones.

Custom Planners
---------------

A planner subclasses :class:`~socm.planner.base.Planner` and implements ``plan``. The
Bookkeeper calls it with the campaign DAG, per-workflow requirements keyed by workflow
ID (``req_cpus``, ``req_memory`` in MB, ``req_walltime`` in minutes), the
``execution_schema`` and ``requested_resources``, and expects a
:class:`~socm.core.models.PlanResult`:

.. code-block:: python

   from socm.core.models import Batch, PlanEntry, PlanResult
   from socm.planner.base import Planner

   class MyPlanner(Planner):
       def plan(self, campaign, resource_requirements, execution_schema=None,
                requested_resources=None, **kargs) -> PlanResult:
           entries = [...]   # one PlanEntry(workflow, cores, memory, start_time, end_time) each
           graph = ...       # the dependency DiGraph of the workflows in this batch
           return PlanResult(qos=None, ncores=requested_resources,
                             batches=[Batch(plan=entries, graph=graph)])

Each ``Batch`` becomes one pilot job; the Bookkeeper runs the batches one after
another. To use the planner, construct it instead of ``HeftPlanner`` in
``Bookkeeper.__init__``.

Custom Enactors
---------------

An enactor subclasses :class:`~socm.enactor.base.Enactor` and runs workflows on a
backend. The Bookkeeper calls:

* ``setup(resource, walltime, cores, execution_schema)`` before each batch, to start
  its allocation;
* ``enact(workflows)`` to submit workflows whose dependencies are done;
* ``teardown()`` after each batch, and ``terminate()`` once at shutdown;
* ``register_state_cb(cb)`` to receive state changes.

The enactor must call every registered callback as
``cb(workflow_ids=[...], new_state=..., step_ids=[...])``:

* ``States.EXECUTING`` when workflows are submitted, with ``None`` step IDs;
* ``States.DONE`` when they succeed, with their SLURM ``"<job_id>.<step_id>"``, which
  the Bookkeeper uses to record them in Slurmise;
* ``States.FAILED`` when they fail or are canceled, with ``None`` step IDs.

``terminate()`` must stop the enactor's monitor thread before returning, so that no
callback arrives after it. ``RPEnactor`` and ``DryrunEnactor`` are the two
implementations; to use another, construct it instead in ``Bookkeeper.__init__``.

Resource Prediction and Slurmise Integration
---------------------------------------------

Recording Job History
~~~~~~~~~~~~~~~~~~~~~

After each workflow finishes, the Bookkeeper records its runtime, memory and
input parameters in a Slurmise database. The parameters come from the workflow
itself: numeric fields are recorded as numerical features, the remaining fields
as categorical ones, and ``file://`` arguments by their MD5 checksum. No
Slurmise job specification is needed.

The database lives in the first of:

1. ``$SOCM_SLURMISE_DIR``, if set
2. ``<campaign base-path>/slurmise_dir``
3. ``<current directory>/slurmise_dir``

Set ``SOCM_SLURMISE_DIR`` to a persistent location so that job history
accumulates across campaigns:

.. code-block:: bash

   export SOCM_SLURMISE_DIR=/scratch/gpfs/SIMONSOBS/users/$USER/slurmise_dir

The Slurmise configuration used by each run is written to
``<session_id>/slurmise.toml``.

.. note::

   Using Slurmise predictions to size workflows is not yet integrated.

Calling socm from Other Tools
-----------------------------

``socm`` is a command-line tool that returns when the campaign ends, so a workflow
manager can run it as one step:

.. code-block:: python

   # Snakefile
   rule campaign:
       input: config="campaign.toml"
       shell: "socm lat-mapmaking -t {input.config}"
