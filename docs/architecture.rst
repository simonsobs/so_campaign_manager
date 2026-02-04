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
2. Planner analyzes workflow dependencies
3. HEFT algorithm computes optimal schedule
4. Resource requirements are estimated (via Slurmise)
5. QoS policies are matched for each workflow
6. Execution plan is generated (list of PlanEntry objects)

**Stage 3: Execution**

1. Enactor receives execution plan
2. SLURM jobs are created for each workflow
3. Jobs are submitted to HPC scheduler
4. RADICAL-Pilot manages task execution
5. State callbacks update workflow status

**Stage 4: Monitoring**

1. Bookkeeper monitors workflow states
2. Enactor provides state updates via callbacks
3. Progress is logged and tracked
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

   class Workflow(BaseModel):
       """Base class for all workflow types."""
       name: str
       executable: str
       context: str
       subcommand: str = ""
       environment: Optional[Dict[str, str]]
       resources: Optional[Dict[str, Union[int, float]]]

       # Abstract methods (must be implemented by subclasses)
       def get_command(self, **kwargs) -> str: ...
       def get_arguments(self, **kwargs) -> str: ...

   class Campaign(BaseModel):
       """Container for workflow collection with policies."""
       id: int
       workflows: List[Workflow]
       campaign_policy: str
       deadline: Optional[int]  # minutes

**Design Patterns:**

* **Template Method:** Workflow base class defines structure, subclasses implement specifics
* **Factory Pattern:** Each workflow type has ``get_workflows()`` class method
* **Strategy Pattern:** Different campaign policies can be plugged in

Bookkeeper (src/socm/bookkeeper/bookkeeper.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Main orchestration engine that coordinates the entire campaign lifecycle.

**Responsibilities:**

1. Initialize campaign from configuration
2. Set up resource management
3. Invoke planner for scheduling
4. Create and configure enactor
5. Monitor workflow execution
6. Handle state transitions
7. Manage cleanup and shutdown

**Key Methods:**

.. code-block:: python

   class Bookkeeper:
       def __init__(self, campaign, resources, policy, target_resource,
                    deadline=None, enactor_config=None):
           """Initialize bookkeeper with campaign and resources."""

       def _create_planner(self) -> BasePlanner:
           """Create planner instance based on policy."""

       def _create_enactor(self) -> BaseEnactor:
           """Create enactor instance for execution."""

       def _plan_campaign(self) -> Tuple[List[PlanEntry], nx.DiGraph]:
           """Generate execution plan using planner."""

       def _execute_plan(self, plan, dag):
           """Execute workflows according to plan."""

       def run(self):
           """Main entry point - runs entire campaign."""

**Integration Points:**

* Integrates with **Slurmise** for SLURM job prediction
* Uses **RADICAL-Utils** for logging and profiling
* Communicates with Planner via defined interface
* Manages Enactor lifecycle and callbacks

Planner (src/socm/planner/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Optimize workflow scheduling to meet campaign deadlines using HEFT algorithm.

**Base Interface (base.py):**

.. code-block:: python

   class PlanEntry:
       """Represents a scheduled workflow execution."""
       workflow: Workflow
       resource_range: Tuple[int, int]  # (start_node, end_node)
       start_time: float  # minutes
       end_time: float  # minutes
       qos: str  # Selected QoS policy

   class BasePlanner(ABC):
       @abstractmethod
       def plan(self, campaign: Campaign, resources: Dict[str, Resource])
                -> Tuple[List[PlanEntry], nx.DiGraph]:
           """Generate execution plan and dependency graph."""

**HEFT Implementation (heft_planner.py):**

The Heterogeneous Earliest Finish Time (HEFT) algorithm consists of:

1. **Rank Computation Phase:**

   * Calculate upward rank for each workflow
   * Rank = computation cost + max(communication cost + successor rank)
   * Workflows with higher rank have higher priority

2. **Processor Selection Phase:**

   * Sort workflows by descending rank
   * For each workflow, find processor that minimizes finish time
   * Consider data transfer costs from parent workflows

3. **Resource Estimation:**

   * Query Slurmise for walltime, CPU, and memory estimates
   * Match estimates against QoS policies
   * Select appropriate QoS tier for each workflow

4. **Plan Generation:**

   * Create PlanEntry for each workflow
   * Assign resource ranges (nodes)
   * Set start/end times
   * Build dependency DAG

**Algorithm Complexity:** O(|V|² × |P|) where V = workflows, P = processors

Enactor (src/socm/enactor/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Execute workflows on HPC systems via SLURM.

**Base Interface (base.py):**

.. code-block:: python

   class BaseEnactor(ABC):
       def __init__(self):
           self._callbacks = defaultdict(list)

       def register_callback(self, state: str, callback: Callable):
           """Register callback for workflow state changes."""

       @abstractmethod
       def submit_workflows(self, plan: List[PlanEntry], dag: nx.DiGraph):
           """Submit workflows according to execution plan."""

       @abstractmethod
       def monitor(self):
           """Monitor workflow execution and trigger callbacks."""

**RADICAL-Pilot Implementation (rp_enactor.py):**

Uses RADICAL-Pilot framework for HPC task execution:

.. code-block:: python

   class RPEnactor(BaseEnactor):
       def __init__(self, resource_config):
           self.session = rp.Session()
           self.pmgr = rp.PilotManager(session=self.session)
           self.tmgr = rp.TaskManager(session=self.session)

       def submit_workflows(self, plan, dag):
           # Create pilot job on HPC resource
           pilot = self.pmgr.submit_pilots(pilot_description)

           # Create tasks for each workflow
           for entry in plan:
               task_desc = self._create_task_description(entry)
               self.tmgr.submit_tasks(task_desc)

       def _create_task_description(self, entry: PlanEntry):
           # Build RADICAL-Pilot TaskDescription
           return rp.TaskDescription({
               'executable': entry.workflow.get_command(),
               'arguments': entry.workflow.get_arguments(),
               'ranks': entry.workflow.resources['ranks'],
               'cores_per_rank': entry.workflow.resources['threads'],
               'environment': entry.workflow.environment,
           })

**State Callbacks:**

Enactor triggers callbacks for state transitions:

* ``SUBMITTED`` - Workflow submitted to scheduler
* ``RUNNING`` - Workflow execution started
* ``COMPLETED`` - Workflow finished successfully
* ``FAILED`` - Workflow encountered error
* ``CANCELLED`` - Workflow was cancelled

**Dryrun Implementation (dryrun_enactor.py):**

Mock implementation for testing without actual execution:

* Simulates workflow execution
* Updates states based on estimated durations
* Useful for testing planning logic

Resources (src/socm/resources/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define HPC resource characteristics and QoS policies.

**Tiger Resource (tiger.py):**

.. code-block:: python

   class TigerResource(Resource):
       """Tiger HPC cluster resource definition."""

       def __init__(self):
           super().__init__(
               name="tiger3",
               nodes=492,
               cores_per_node=112,
               memory_per_node=1000000,  # MB
               qos=self._get_qos_policies()
           )

       def _get_qos_policies(self) -> List[QosPolicy]:
           return [
               QosPolicy(name="test", max_walltime=60),
               QosPolicy(name="vshort", max_walltime=300),
               QosPolicy(name="short", max_walltime=1440),
               QosPolicy(name="medium", max_walltime=4320),
               QosPolicy(name="long", max_walltime=8640),
               QosPolicy(name="vlong", max_walltime=21600),
           ]

       def register_job(self, workflow: Workflow) -> str:
           """Select appropriate QoS based on workflow requirements."""
           runtime = workflow.resources.get('runtime', 0)
           for qos in sorted(self.qos, key=lambda q: q.max_walltime):
               if runtime <= qos.max_walltime * 60:  # Convert to seconds
                   return qos.name
           return self.qos[-1].name  # Default to longest QoS

Workflows (src/socm/workflows/)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define specific analysis tasks and their execution parameters.

**Workflow Registry:**

All workflows must be registered in ``workflows/__init__.py``:

.. code-block:: python

   registered_workflows = {
       "ml-mapmaking": MLMapmakingWorkflow,
       "sat-sims": SATSimWorkflow,
       "ml-null-tests.mission-tests": TimeNullTestWorkflow,
       "ml-null-tests.wafer-tests": WaferNullTestWorkflow,
       "ml-null-tests.direction-tests": DirectionNullTestWorkflow,
       # ... more null tests
   }

   subcampaign_map = {
       "ml-null-tests": [
           "mission-tests", "wafer-tests", "direction-tests",
           "pwv-tests", "day-night-tests", "moonrise-set-tests",
           "elevation-tests", "sun-close-tests", "moon-close-tests"
       ]
   }

**Workflow Implementation Pattern:**

Each workflow must:

1. Inherit from ``Workflow`` base class
2. Define workflow-specific parameters as Pydantic fields
3. Implement ``get_command()`` method
4. Implement ``get_arguments()`` method
5. Provide ``get_workflows()`` class method for factory pattern

**Example: ML Mapmaking Workflow**

.. code-block:: python

   class MLMapmakingWorkflow(Workflow):
       # Workflow-specific parameters
       area: str
       bands: str
       output_dir: str
       maxiter: str = "100"
       tiled: int = 0

       def get_command(self, **kwargs) -> str:
           return f"{self.executable} {self.subcommand}"

       def get_arguments(self, **kwargs) -> str:
           args = [
               f"--context {self.context}",
               f"--area {self.area}",
               f"--bands {self.bands}",
               f"--output-dir {self.output_dir}",
               f"--maxiter {self.maxiter}",
           ]
           if self.tiled:
               args.append("--tiled")
           return " ".join(args)

       @classmethod
       def get_workflows(cls, descriptions: List[Dict]) -> List['MLMapmakingWorkflow']:
           """Factory method to create workflow instances."""
           return [cls(**desc) for desc in descriptions]

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
   bands = "f090"

   [campaign.ml-null-tests.mission-tests]
   # Mission-test specific configuration
   chunk_nobs = 10
   nsplits = 4

The ``mission-tests`` workflow inherits ``context``, ``area``, and ``bands`` from parent.

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

* **Explicit dependencies** - Defined in configuration
* **Implicit dependencies** - Inferred from data flow
* **Dependency DAG** - Built by planner using NetworkX

**Dependency Resolution:**

1. Planner constructs directed acyclic graph (DAG)
2. Topological sort determines execution order
3. HEFT algorithm schedules within dependency constraints
4. Enactor enforces dependencies during submission

State Management
----------------

Workflow State Machine
~~~~~~~~~~~~~~~~~~~~~~~

Each workflow transitions through defined states:

::

    INITIAL → SUBMITTED → RUNNING → COMPLETED
                                  ↘ FAILED
                                  ↘ CANCELLED

**State Definitions (utils/states.py):**

.. code-block:: python

   class WorkflowState:
       INITIAL = "INITIAL"
       SUBMITTED = "SUBMITTED"
       RUNNING = "RUNNING"
       COMPLETED = "COMPLETED"
       FAILED = "FAILED"
       CANCELLED = "CANCELLED"

**State Transitions:**

* Managed by Enactor via RADICAL-Pilot callbacks
* Logged for monitoring and debugging
* Trigger downstream workflow activation when dependencies complete

Integration with External Systems
----------------------------------

SLURM Integration
~~~~~~~~~~~~~~~~~

The system integrates with SLURM scheduler via two mechanisms:

1. **RADICAL-Pilot**: Submits and manages SLURM jobs
2. **Slurmise**: Predicts resource requirements

**Slurmise Integration:**

Slurmise provides ML-based prediction of:

* Walltime estimation
* CPU requirements
* Memory requirements

Based on workflow characteristics (numeric and categorical features).

RADICAL-Pilot Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

RADICAL-Pilot provides:

* Pilot job management
* Task scheduling within pilot
* State monitoring and callbacks
* Resource allocation within SLURM allocation

**Session Management:**

.. code-block:: python

   session = rp.Session()
   try:
       pmgr = rp.PilotManager(session=session)
       tmgr = rp.TaskManager(session=session)
       # Execute workflows
   finally:
       session.close()

Error Handling and Recovery
----------------------------

Failure Scenarios
~~~~~~~~~~~~~~~~~

The system handles various failure modes:

1. **Configuration Errors:** Validation fails during parsing
2. **Resource Allocation Failures:** SLURM rejects job
3. **Workflow Execution Failures:** Task crashes or times out
4. **System Failures:** Node crashes, network issues

**Error Handling Strategies:**

* **Validation:** Pydantic validates all input data
* **Graceful Degradation:** Log errors and continue with remaining workflows
* **State Tracking:** Failed workflows marked in state machine
* **Cleanup:** Session cleanup in finally blocks

Performance Considerations
--------------------------

Optimization Strategies
~~~~~~~~~~~~~~~~~~~~~~~

1. **Efficient Scheduling:** HEFT algorithm minimizes makespan
2. **Resource Packing:** Maximize node utilization
3. **QoS Selection:** Automatic selection of appropriate queue
4. **Parallel Execution:** Independent workflows run concurrently

Scalability
~~~~~~~~~~~

The system scales to:

* **Hundreds of workflows** in a single campaign
* **Thousands of nodes** on large HPC systems
* **Long-running campaigns** (days to weeks)

Extensibility
-------------

Adding New Components
~~~~~~~~~~~~~~~~~~~~~

The architecture supports extension through:

**New Workflow Types:**

1. Create workflow class inheriting from ``Workflow``
2. Implement required methods
3. Register in ``registered_workflows`` dict

**New Planners:**

1. Create planner class inheriting from ``BasePlanner``
2. Implement ``plan()`` method
3. Update Bookkeeper to instantiate new planner

**New Enactors:**

1. Create enactor class inheriting from ``BaseEnactor``
2. Implement required methods
3. Configure Bookkeeper to use new enactor

**New Resources:**

1. Create resource class inheriting from ``Resource``
2. Define QoS policies
3. Implement resource-specific logic

Design Principles
-----------------

The architecture follows these key principles:

1. **Separation of Concerns:** Each component has single responsibility
2. **Interface-based Design:** Abstract base classes define contracts
3. **Dependency Injection:** Components receive dependencies via constructors
4. **Configuration over Code:** TOML configuration drives behavior
5. **Fail-Fast Validation:** Pydantic validates early
6. **Logging and Observability:** Comprehensive logging throughout
7. **Testability:** Modular design enables unit testing

Testing Architecture
--------------------

The test suite mirrors the package structure:

* **Unit Tests:** Test individual components in isolation
* **Integration Tests:** Test component interactions
* **Mock Objects:** DryrunEnactor for testing without HPC
* **Fixtures:** Reusable test data in ``conftest.py``
* **Property-Based Testing:** Hypothesis for edge cases

Summary
-------

The SO Campaign Manager architecture provides:

* **Modularity:** Clean separation of concerns
* **Extensibility:** Easy to add new workflows and backends
* **Robustness:** Validation and error handling throughout
* **Scalability:** Handles large campaigns on massive HPC systems
* **Maintainability:** Clear interfaces and comprehensive tests

The design enables efficient orchestration of complex mapmaking campaigns while remaining flexible and maintainable.
