Architecture
============

This document provides a comprehensive overview of the SO Campaign Manager architecture, design patterns, and internal workings.

System Overview
---------------

SO Campaign Manager is built on a modular architecture that separates concerns into distinct components:


Core Components
---------------

The system consists of five major components that work together to orchestrate HPC workflow campaigns:

1. **Core Models** - Data structures and validation
2. **Bookkeeper** - Main orchestration engine
3. **Planner** - Workflow scheduling and optimization
4. **Enactor** - Execution backends
5. **Workflows** - Task definitions and implementations

Component Diagram
~~~~~~~~~~~~~~~~~

::

    ┌─────────────────────────────────────────────────────────────┐
    │                         Bookkeeper                          │
    │   (Main Orchestrator - Coordinates All Components)          │
    └──────────┬──────────────────────────────────┬───────────────┘
               │                                  │
               │                                  │
    ┌──────────▼──────────┐            ┌─────────▼──────────┐
    │      Planner        │            │      Enactor       │
    │  (HEFT Algorithm)   │            │  (RADICAL-Pilot)   │
    └──────────┬──────────┘            └─────────┬──────────┘
               │                                  │
               │         ┌────────────────────────┘
               │         │
    ┌──────────▼─────────▼───────────┐
    │       Core Models              │
    │  (Campaign, Workflow, Resource)│
    └───────────────┬────────────────┘
                    │
         ┌──────────▼──────────┐
         │     Workflows       │
         │  (ML Mapmaking,     │
         │   Null Tests, etc.) │
         └─────────────────────┘

Data Flow
---------

The typical data flow through the system follows these stages:

Configuration → Planning → Execution → Monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Stage 1: Configuration Parsing**

1. User provides TOML configuration file
2. Configuration parser reads campaign settings
3. Workflow entries are extracted and validated
4. Workflow factory classes create instances
5. Campaign object is constructed with all workflows

**Stage 2: Planning**

1. Bookkeeper receives Campaign and Resource objects
2. Planner analyzes workflow dependencies from the DAG
3. HEFT algorithm computes optimal schedule
4. Resource requirements are estimated (via Slurmise or workflow ``resources`` field)
5. QoS policies are matched for the campaign deadline
6. Execution plan is generated (list of ``PlanEntry`` objects, one or more ``Batch`` objects)

**Stage 3: Execution**

1. Enactor receives execution plan
2. RADICAL-Pilot pilot job is submitted to SLURM
3. Workflows are submitted as RP tasks within the pilot
4. State callbacks update workflow status in the Bookkeeper

**Stage 4: Monitoring**

1. Bookkeeper monitors workflow states
2. Enactor provides state updates via callbacks
3. Progress is logged and profiled via RADICAL-Utils
4. Completion or failure triggers next actions

Detailed Component Architecture
--------------------------------

Core Models (src/socm/core/models.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define data structures with validation using Pydantic v2.

**Key Classes:**

.. code-block:: python

   class QosPolicy(BaseModel):
       """SLURM Quality of Service policy definition."""
       name: str
       max_walltime: Optional[int]  # minutes
       max_jobs: Optional[int]
       max_cores: Optional[int]

   class Resource(BaseModel):
       """HPC resource specification."""
       name: str
       nodes: int
       cores_per_node: int
       memory_per_node: int
       qos: List[QosPolicy]

   class ResourceSpec(BaseModel):
       """Per-workflow resource specification (ranks, threads, runtime)."""
       ranks: int = 1
       threads: int = 1
       runtime: float = 60  # minutes

   class Workflow(BaseModel):
       """Base class for all workflow types."""
       name: str
       executable: str
       context: str
       subcommand: str = ""
       environment: Optional[Dict[str, str]]
       resources: ResourceSpec  # ResourceSpec object, not a plain dict

       # Abstract methods (must be implemented by subclasses)
       def get_command(self) -> str: ...
       def get_arguments(self) -> List[str]: ...

   class Campaign(BaseModel):
       """Container for workflow collection with policies."""
       id: int
       workflows: DAG          # DAG object, not a plain list
       campaign_policy: str
       deadline: str           # string, e.g. "2d"
       execution_schema: str   # "batch" or "remote"
       requested_resources: int

   class PlanEntry(NamedTuple):
       """A single scheduled workflow entry in the execution plan."""
       workflow: Workflow
       cores: range
       memory: float
       start_time: float
       end_time: float

   class Batch(NamedTuple):
       """A group of workflows that execute within a single pilot submission."""
       plan: List[PlanEntry]
       graph: nx.DiGraph

   class PlanResult(NamedTuple):
       """Complete output of the planning phase."""
       qos: Optional[QosPolicy]
       ncores: int
       batches: List[Batch]

**Design Patterns:**

* **Template Method:** Workflow base class defines structure, subclasses implement specifics
* **Factory Pattern:** Each workflow type has ``get_workflows()`` class method
* **Strategy Pattern:** Different campaign policies can be plugged in

Bookkeeper (src/socm/bookkeeper/bookkeeper.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Main orchestration engine that coordinates the entire campaign lifecycle.

**Constructor Signature:**

.. code-block:: python

   class Bookkeeper:
       def __init__(
           self,
           campaign: Campaign,
           policy: str,
           target_resource: str,
           deadline: float,
           dryrun: bool = False,
       ):
           """Initialize bookkeeper with campaign and resources."""

**Responsibilities:**

1. Initialize campaign from configuration
2. Set up resource management (looks up ``target_resource`` in ``registered_resources``)
3. Invoke planner for scheduling
4. Create and configure enactor (``RPEnactor`` or ``DryrunEnactor``)
5. Monitor workflow execution via state callbacks
6. Handle state transitions
7. Manage cleanup and shutdown

**Key Methods:**

.. code-block:: python

   def run(self):
       """Main entry point — spawns work and monitor threads."""

   def work(self):
       """Plan and submit workflows (runs in dedicated thread)."""

   def monitor(self):
       """Monitor workflow states and record execution data (runs in dedicated thread)."""

   def terminate(self):
       """Gracefully shut down enactor and all threads."""

   def get_makespan(self) -> float:
       """Return estimated campaign makespan in minutes."""

   def get_campaign_state(self) -> States:
       """Return current campaign state."""

   def get_workflows_state(self) -> Dict[str, States]:
       """Return per-workflow state dictionary."""

**Integration Points:**

* Integrates with **Slurmise** for SLURM job prediction and post-execution recording
* Uses **RADICAL-Utils** for logging and profiling
* Communicates with Planner via ``plan()`` interface
* Manages Enactor lifecycle and callbacks

Planner (src/socm/planner/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Optimize workflow scheduling to meet campaign deadlines using HEFT algorithm.

**Base Interface (base.py):**

.. code-block:: python

   class Planner:
       def __init__(
           self,
           campaign=None,
           resources=None,
           resource_requirements=None,
           policy=None,
           sid=None,
           objective=None,
       ):
           """Initialize planner with campaign and resource information."""

       def plan(self, campaign, resource_requirements, execution_schema, requested_resources) -> PlanResult:
           """Generate execution plan and return PlanResult."""

       def replan(self, campaign, resources, resource_requirements, start_time) -> Tuple[List[PlanEntry], DiGraph]:
           """Recalculate plan after workflow completion."""

**HEFT Implementation (heft_planner.py):**

The Heterogeneous Earliest Finish Time (HEFT) algorithm consists of:

1. **Resource Estimation Phase:**

   * Per-workflow ``req_cpus``, ``req_memory``, ``req_walltime`` are obtained from
     workflow resources (with a 10% runtime buffer) or predicted via Slurmise.

2. **Processor Selection Phase (for each dependency level):**

   * Sort workflows by descending estimated walltime (longest-first heuristic).
   * For each workflow, slide a core window across the resource array and select
     the slot that yields the earliest finish time.
   * Memory constraints are respected: slots with insufficient free memory are skipped.

3. **QoS Selection (remote mode):**

   * Binary search for the minimum core count that meets the campaign deadline.
   * If no single QoS tier covers both cores and deadline, the plan is split into
     sequential batches.

4. **Plan Generation:**

   * Create ``PlanEntry`` objects with workflow, core range, memory, start/end times.
   * Build a dependency ``DiGraph`` from core-sharing relationships.
   * Wrap in ``Batch`` and ``PlanResult`` objects.

**Algorithm Complexity:** O(|V|² × |P|) where V = workflows, P = cores

Enactor (src/socm/enactor/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Execute workflows on HPC systems via SLURM.

**Base Interface (base.py):**

.. code-block:: python

   class Enactor:
       def __init__(self, sid):
           """Initialize enactor with session ID."""

       def setup(self, resource, walltime, cores, execution_schema=None):
           """Set up the execution backend (create pilot job)."""

       def enact(self, workflows):
           """Submit workflows for execution."""

       def get_status(self, workflows=None) -> Dict[str, States]:
           """Return current state of one or more workflows."""

       def terminate(self):
           """Terminate the enactor and clean up resources."""

       def teardown(self):
           """Cancel the current pilot (called between batches)."""

       def register_state_cb(self, cb):
           """Register a callback for state-change notifications."""

**RADICAL-Pilot Implementation (rp_enactor.py):**

Uses RADICAL-Pilot framework for HPC task execution:

.. code-block:: python

   class RPEnactor(Enactor):
       def setup(self, resource, walltime, cores, execution_schema=None):
           # Submit pilot job and wait for PMGR_ACTIVE
           pdesc = rp.PilotDescription({"resource": f"so.{resource.name}", "cores": cores, ...})
           self._pilot = self._rp_pmgr.submit_pilots(pdesc)
           self._pilot.wait(state=rp.PMGR_ACTIVE)

       def enact(self, workflows):
           # Build rp.TaskDescription from each workflow's resources and arguments
           for workflow in workflows:
               td = rp.TaskDescription()
               td.executable = workflow.executable
               td.arguments = [workflow.subcommand] + workflow.get_arguments()
               td.ranks = workflow.resources.ranks
               td.cores_per_rank = workflow.resources.threads
               self._rp_tmgr.submit_tasks([td])

**State Callbacks:**

Enactor invokes registered callbacks with ``workflow_ids``, ``new_state``, and
``step_ids`` when workflows reach ``EXECUTING`` or ``DONE`` states.

**Dryrun Implementation (dryrun_enactor.py):**

Mock implementation for testing without actual execution:

* Simulates workflow execution transitions
* Useful for testing planning and bookkeeping logic without an HPC allocation

Resources (src/socm/resources/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define HPC resource characteristics and QoS policies.

Three pre-configured resource classes are provided:

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 20

   * - Class
     - Resource key
     - Nodes
     - Cores/node
   * - ``TigerResource``
     - ``tiger3``
     - 492
     - 112
   * - ``PerlmutterResource``
     - ``perlmutter``
     - 3 072
     - 128
   * - ``UniverseResource``
     - ``universe``
     - 28
     - 224

See :doc:`resources` for the full QoS tier specifications.

Workflows (src/socm/workflows/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define specific analysis tasks and their execution parameters.

**Workflow Registry:**

All workflows must be registered in ``workflows/__init__.py``:

.. code-block:: python

   registered_workflows = {
       "power-spectra": SpectraWorkflow,
       "sat-sims": SATSimWorkflow,
       "ml-mapmaking": MLMapmakingWorkflow,
       "ml-null-tests.mission-tests": TimeNullTestWorkflow,
       "ml-null-tests.wafer-tests": WaferNullTestWorkflow,
       "ml-null-tests.direction-tests": DirectionNullTestWorkflow,
       "ml-null-tests.pwv-tests": PWVNullTestWorkflow,
       "ml-null-tests.day-night-tests": DayNightNullTestWorkflow,
       "ml-null-tests.moonrise-set-tests": MoonRiseSetNullTestWorkflow,
       "ml-null-tests.elevation-tests": ElevationNullTestWorkflow,
       "ml-null-tests.sun-close-tests": SunCloseFarNullTestWorkflow,
       "ml-null-tests.moon-close-tests": MoonCloseFarNullTestWorkflow,
       "ml-null-tests.smart-split-tests": SmartSplitNullTestWorkflow,
   }

   subcampaign_map = {
       "ml-null-tests": [
           "mission-tests", "wafer-tests", "direction-tests",
           "pwv-tests", "day-night-tests", "moonrise-set-tests",
           "elevation-tests", "sun-close-tests", "moon-close-tests",
           "smart-split-tests",
       ]
   }

**Workflow Implementation Pattern:**

Each workflow must:

1. Inherit from ``Workflow`` base class
2. Define workflow-specific parameters as Pydantic fields
3. Implement ``get_command() -> str`` method
4. Implement ``get_arguments() -> List[str]`` method (returns a *list* of strings,
   not a single string)
5. Provide ``get_workflows()`` class method for factory pattern

Configuration System
--------------------

TOML-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration system uses TOML for human-readable campaign definitions.

**Hierarchical Structure:**

1. **Top-level campaign section** - Global settings
2. **Workflow sections** - Workflow-specific configuration
3. **Subcampaign sections** - Groups of related workflows
4. **Resource sections** - Per-workflow resource requirements

**Configuration Inheritance:**

Subcampaign workflows inherit common configuration from parent:

.. code-block:: toml

   [campaign.ml-null-tests]
   # Common configuration for all null tests
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   preprocess_config = "file:///path/to/preprocess.yaml"

   [campaign.ml-null-tests.mission-tests]
   # Mission-test specific configuration
   chunk_nobs = 10
   nsplits = 8

The ``mission-tests`` workflow inherits ``context``, ``area``, and
``preprocess_config`` from the parent section.

**Configuration Parsing:**

The ``get_workflow_entries()`` utility in ``utils/misc.py`` handles:

* Parsing TOML structure
* Expanding subcampaign hierarchies
* Merging inherited configuration
* Creating workflow descriptions

Dependency Management
---------------------

Workflow Dependencies
~~~~~~~~~~~~~~~~~~~~~

The system supports dependency relationships between workflows:

* **Explicit dependencies** - Defined in the ``depends`` field of each workflow
* **DAG Construction** - Built by the ``Campaign.validate_workflows`` validator using
  NetworkX ``DiGraph``

**Dependency Resolution:**

1. ``Campaign`` validator constructs the DAG from ``depends`` lists
2. ``DAG.levels`` property returns workflows grouped by topological generation
3. HEFT algorithm schedules within dependency constraints (per level)
4. Enactor respects dependencies: workflows wait for all predecessors to reach ``DONE``

State Management
----------------

Workflow State Machine
~~~~~~~~~~~~~~~~~~~~~~~

Each workflow and campaign transitions through defined states defined in
``utils/states.py``:

.. code-block:: python

   class States(Enum):
       NEW = auto()        # Not yet submitted
       PLANNING = auto()   # Campaign is being planned
       EXECUTING = auto()  # At least one workflow is executing
       DONE = auto()       # Finished successfully
       FAILED = auto()     # Execution failed
       CANCELED = auto()   # Cancelled by user

Final states (``CFINAL``) are ``[DONE, FAILED, CANCELED]``.

::

    NEW → PLANNING → EXECUTING → DONE
                              ↘ FAILED
                              ↘ CANCELED

**State Transitions:**

* Managed by the Enactor via RADICAL-Pilot callbacks
* Logged via RADICAL-Utils Logger and Profiler
* Trigger downstream workflow activation when all dependencies reach ``DONE``

Integration with External Systems
----------------------------------

SLURM Integration
~~~~~~~~~~~~~~~~~

The system integrates with SLURM scheduler via two mechanisms:

1. **RADICAL-Pilot**: Submits and manages SLURM jobs via a pilot allocation
2. **Slurmise**: Records and predicts resource requirements for workflows

**Slurmise Integration:**

After each workflow completes, the Bookkeeper calls ``_record()`` to store
execution metadata (runtime, memory, categorical/numerical workflow fields)
via ``Slurmise.raw_record()``. Future runs can use these records to predict
resource requirements, reducing over-allocation.

RADICAL-Pilot Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

RADICAL-Pilot provides:

* Pilot job management (one pilot per batch)
* Task scheduling within the pilot
* State monitoring via task queries
* Resource allocation within the SLURM job

**Session Management:**

.. code-block:: python

   session = rp.Session(uid=sid)
   pmgr = rp.PilotManager(session=session)
   tmgr = rp.TaskManager(session=session)
   # ... submit pilot and tasks ...
   pmgr.close(terminate=True)
   session.close(terminate=True)

Error Handling and Recovery
----------------------------

Failure Scenarios
~~~~~~~~~~~~~~~~~

The system handles various failure modes:

1. **Configuration Errors:** Pydantic validation fails during parsing
2. **Planning Failures:** No QoS policy can accommodate the deadline
3. **Resource Allocation Failures:** SLURM rejects pilot job
4. **Workflow Execution Failures:** Task crashes or times out

**Error Handling Strategies:**

* **Validation:** Pydantic validates all input data at construction time
* **Exception Logging:** Exceptions in the work thread are caught, logged, and the
  campaign state is set to ``FAILED``
* **State Tracking:** Failed workflows are reflected in the state dictionary
* **Cleanup:** ``terminate()`` is always called in a ``finally`` block in ``run()``

Performance Considerations
--------------------------

Optimization Strategies
~~~~~~~~~~~~~~~~~~~~~~~

1. **Efficient Scheduling:** HEFT algorithm minimises makespan
2. **Binary Search:** Minimum core count found via binary search over the QoS range
3. **Batch Splitting:** When no single QoS tier fits, the plan is split into sequential
   pilot submissions
4. **QoS Selection:** Automatic selection of the most appropriate SLURM queue
5. **Parallel Execution:** Independent workflows within each dependency level run concurrently

Scalability
~~~~~~~~~~~

The system scales to:

* **Hundreds of workflows** in a single campaign
* **Thousands of nodes** on large HPC systems
* **Long-running campaigns** split across multiple pilot submissions

Extensibility
-------------

Adding New Components
~~~~~~~~~~~~~~~~~~~~~

The architecture supports extension through:

**New Workflow Types:**

1. Create workflow class inheriting from ``Workflow``
2. Implement ``get_command() -> str`` and ``get_arguments() -> List[str]``
3. Register in ``registered_workflows`` dict

**New Planners:**

1. Create planner class inheriting from ``Planner``
2. Implement ``plan()`` method returning a ``PlanResult``
3. Update Bookkeeper to instantiate new planner

**New Enactors:**

1. Create enactor class inheriting from ``Enactor``
2. Implement required methods
3. Configure Bookkeeper to use new enactor

**New Resources:**

1. Create resource class inheriting from ``Resource``
2. Define QoS policies in ``__init__``
3. Register in ``resources/__init__.py``'s ``registered_resources`` dict

Design Principles
-----------------

The architecture follows these key principles:

1. **Separation of Concerns:** Each component has a single responsibility
2. **Interface-based Design:** Abstract base classes define contracts
3. **Dependency Injection:** Components receive dependencies via constructors
4. **Configuration over Code:** TOML configuration drives behavior
5. **Fail-Fast Validation:** Pydantic validates early
6. **Logging and Observability:** Comprehensive logging via RADICAL-Utils throughout
7. **Testability:** Modular design with DryrunEnactor enables unit testing

Testing Architecture
--------------------

The test suite mirrors the package structure:

* **Unit Tests:** Test individual components in isolation
* **Integration Tests:** Test component interactions
* **Mock Objects:** DryrunEnactor for testing without HPC allocation
* **Fixtures:** Reusable test data in ``conftest.py``

Summary
-------

The SO Campaign Manager architecture provides:

* **Modularity:** Clean separation of concerns
* **Extensibility:** Easy to add new workflows and backends
* **Robustness:** Validation and error handling throughout
* **Scalability:** Handles large campaigns on massive HPC systems
* **Maintainability:** Clear interfaces and comprehensive tests

The design enables efficient orchestration of complex mapmaking campaigns while remaining flexible and maintainable.
