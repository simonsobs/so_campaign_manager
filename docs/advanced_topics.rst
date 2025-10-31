Advanced Topics
===============

This guide covers advanced features and use cases of SO Campaign Manager for power users and developers.

Custom Workflow Development
----------------------------

Creating a New Workflow Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a custom workflow type to SO Campaign Manager, follow these steps:

**Step 1: Define the Workflow Class**

Create a new Python file in ``src/socm/workflows/``:

.. code-block:: python

   # src/socm/workflows/my_custom_workflow.py
   from typing import Dict, List, Optional
   from socm.core.models import Workflow

   class MyCustomWorkflow(Workflow):
       """Custom workflow for specific analysis task.

       Args:
           custom_param1: Description of first custom parameter
           custom_param2: Description of second custom parameter
           threshold: Analysis threshold value
       """

       # Define workflow-specific parameters
       custom_param1: str
       custom_param2: Optional[str] = None
       threshold: float = 0.5

       def get_command(self, **kwargs) -> str:
           """Build the command to execute.

           Returns:
               Complete command string including executable and subcommand
           """
           cmd_parts = [self.executable]
           if self.subcommand:
               cmd_parts.append(self.subcommand)
           return " ".join(cmd_parts)

       def get_arguments(self, **kwargs) -> str:
           """Build command-line arguments.

           Returns:
               Space-separated argument string
           """
           args = [
               f"--context {self.context}",
               f"--param1 {self.custom_param1}",
               f"--threshold {self.threshold}",
           ]

           if self.custom_param2:
               args.append(f"--param2 {self.custom_param2}")

           return " ".join(args)

       @classmethod
       def get_workflows(cls, descriptions: List[Dict]) -> List['MyCustomWorkflow']:
           """Factory method to create workflow instances from configuration.

           Args:
               descriptions: List of workflow configuration dictionaries

           Returns:
               List of instantiated workflow objects
           """
           workflows = []
           for desc in descriptions:
               workflow = cls(**desc)
               workflows.append(workflow)
           return workflows

**Step 2: Register the Workflow**

Add your workflow to the registry in ``src/socm/workflows/__init__.py``:

.. code-block:: python

   from .my_custom_workflow import MyCustomWorkflow

   registered_workflows = {
       # ... existing workflows
       'my-custom-workflow': MyCustomWorkflow,
   }

**Step 3: Add to Subcampaign Map (if applicable)**

If your workflow is part of a subcampaign:

.. code-block:: python

   subcampaign_map = {
       # ... existing mappings
       'my-custom-analysis': ['my-custom-workflow'],
   }

**Step 4: Create Configuration Template**

Document the TOML configuration format:

.. code-block:: toml

   [campaign.my-custom-workflow]
   context = "file:///path/to/context.yaml"
   custom_param1 = "value1"
   custom_param2 = "value2"
   threshold = 0.75

   [campaign.my-custom-workflow.resources]
   ranks = 16
   threads = 4
   memory = "64000"
   runtime = "2h"

   [campaign.my-custom-workflow.environment]
   CUSTOM_ENV_VAR = "value"

**Step 5: Add Tests**

Create comprehensive tests in ``tests/workflows/test_my_custom_workflow.py``:

.. code-block:: python

   import pytest
   from socm.workflows.my_custom_workflow import MyCustomWorkflow

   def test_workflow_creation():
       """Test basic workflow instantiation."""
       workflow = MyCustomWorkflow(
           name="test_workflow",
           executable="my-tool",
           context="/path/to/context.yaml",
           custom_param1="value1",
           threshold=0.8
       )
       assert workflow.custom_param1 == "value1"
       assert workflow.threshold == 0.8

   def test_get_command():
       """Test command generation."""
       workflow = MyCustomWorkflow(
           name="test",
           executable="my-tool",
           subcommand="analyze",
           context="/path/to/context.yaml",
           custom_param1="value1"
       )
       cmd = workflow.get_command()
       assert cmd == "my-tool analyze"

   def test_get_arguments():
       """Test argument generation."""
       workflow = MyCustomWorkflow(
           name="test",
           executable="my-tool",
           context="/path/to/context.yaml",
           custom_param1="value1",
           threshold=0.9
       )
       args = workflow.get_arguments()
       assert "--context /path/to/context.yaml" in args
       assert "--param1 value1" in args
       assert "--threshold 0.9" in args

   def test_factory_method():
       """Test workflow factory method."""
       descriptions = [
           {
               "name": "workflow1",
               "executable": "my-tool",
               "context": "/path/to/context.yaml",
               "custom_param1": "value1"
           },
           {
               "name": "workflow2",
               "executable": "my-tool",
               "context": "/path/to/context.yaml",
               "custom_param1": "value2"
           }
       ]
       workflows = MyCustomWorkflow.get_workflows(descriptions)
       assert len(workflows) == 2
       assert workflows[0].custom_param1 == "value1"
       assert workflows[1].custom_param1 == "value2"

Advanced Workflow Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Numeric and Categorical Fields**

Workflows can define which fields are numeric or categorical for resource estimation:

.. code-block:: python

   class MyWorkflow(Workflow):
       numeric_field: int
       categorical_field: str

       def get_numeric_fields(self, avoid_attributes=None) -> List[str]:
           """Return list of numeric field names for resource estimation."""
           fields = super().get_numeric_fields(avoid_attributes)
           # Customize if needed
           return fields

       def get_categorical_fields(self, avoid_attributes=None) -> List[str]:
           """Return list of categorical field names."""
           # Implementation
           return ["categorical_field"]

**Dynamic Resource Requirements**

Calculate resources based on workflow parameters:

.. code-block:: python

   class AdaptiveWorkflow(Workflow):
       data_size_gb: float

       def estimate_resources(self) -> Dict[str, int]:
           """Dynamically estimate resource needs based on data size."""
           # Rule: 1 rank per 2 GB of data
           ranks = max(1, int(self.data_size_gb / 2))

           # Memory: 2x data size + 50GB overhead
           memory_mb = int(self.data_size_gb * 2000 + 50000)

           return {
               "ranks": ranks,
               "threads": 8,
               "memory": memory_mb,
               "runtime": "4h"
           }

Custom Planner Development
---------------------------

Implementing a Custom Scheduling Algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If HEFT doesn't meet your needs, implement a custom planner:

**Step 1: Create Planner Class**

.. code-block:: python

   # src/socm/planner/my_planner.py
   from typing import Dict, List, Tuple
   import networkx as nx
   from socm.planner.base import BasePlanner, PlanEntry
   from socm.core.models import Campaign, Resource

   class MyCustomPlanner(BasePlanner):
       """Custom planning algorithm implementation."""

       def __init__(self, **kwargs):
           super().__init__()
           self.config = kwargs

       def plan(
           self,
           campaign: Campaign,
           resources: Dict[str, Resource]
       ) -> Tuple[List[PlanEntry], nx.DiGraph]:
           """Generate execution plan using custom algorithm.

           Args:
               campaign: Campaign containing workflows to schedule
               resources: Available HPC resources

           Returns:
               Tuple of (execution plan, dependency DAG)
           """
           # Build dependency graph
           dag = self._build_dependency_graph(campaign.workflows)

           # Your custom scheduling logic here
           plan = self._custom_scheduling_algorithm(
               campaign.workflows,
               resources,
               dag
           )

           return plan, dag

       def _build_dependency_graph(
           self,
           workflows: List[Workflow]
       ) -> nx.DiGraph:
           """Construct workflow dependency graph."""
           dag = nx.DiGraph()

           for workflow in workflows:
               dag.add_node(workflow.name, workflow=workflow)

           # Add edges based on dependencies
           # Example: parse dependency info from workflow metadata
           for workflow in workflows:
               if hasattr(workflow, 'depends_on'):
                   for dep in workflow.depends_on:
                       dag.add_edge(dep, workflow.name)

           return dag

       def _custom_scheduling_algorithm(
           self,
           workflows: List[Workflow],
           resources: Dict[str, Resource],
           dag: nx.DiGraph
       ) -> List[PlanEntry]:
           """Implement your scheduling algorithm."""
           plan = []

           # Example: Simple greedy scheduling
           sorted_workflows = nx.topological_sort(dag)

           current_time = 0
           for wf_name in sorted_workflows:
               workflow = dag.nodes[wf_name]['workflow']

               # Estimate runtime
               runtime = self._estimate_runtime(workflow)

               # Allocate resources
               resource_range = self._allocate_resources(workflow, resources)

               # Create plan entry
               entry = PlanEntry(
                   workflow=workflow,
                   resource_range=resource_range,
                   start_time=current_time,
                   end_time=current_time + runtime,
                   qos=self._select_qos(runtime, resources)
               )
               plan.append(entry)

               # Update time (sequential for simplicity)
               current_time += runtime

           return plan

       def _estimate_runtime(self, workflow: Workflow) -> float:
           """Estimate workflow runtime in minutes."""
           # Use provided runtime or estimate
           if workflow.resources and 'runtime' in workflow.resources:
               return self._parse_time(workflow.resources['runtime'])
           return 60.0  # Default 1 hour

       def _allocate_resources(
           self,
           workflow: Workflow,
           resources: Dict[str, Resource]
       ) -> Tuple[int, int]:
           """Allocate node range for workflow."""
           # Simple allocation: return (start_node, end_node)
           ranks = workflow.resources.get('ranks', 1)
           resource = list(resources.values())[0]
           cores_per_node = resource.cores_per_node

           nodes_needed = (ranks + cores_per_node - 1) // cores_per_node
           return (0, nodes_needed)

       def _select_qos(
           self,
           runtime: float,
           resources: Dict[str, Resource]
       ) -> str:
           """Select appropriate QoS based on runtime."""
           resource = list(resources.values())[0]
           for qos in sorted(resource.qos, key=lambda q: q.max_walltime):
               if runtime <= qos.max_walltime:
                   return qos.name
           return resource.qos[-1].name

**Step 2: Register Planner**

Update Bookkeeper to support your planner:

.. code-block:: python

   # In bookkeeper.py
   def _create_planner(self):
       if self.policy == "time":
           return HeftPlanner()
       elif self.policy == "custom":
           return MyCustomPlanner()
       else:
           raise ValueError(f"Unknown policy: {self.policy}")

Custom Enactor Development
---------------------------

Implementing Alternative Execution Backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create custom enactor for different execution environments:

**Step 1: Define Enactor Class**

.. code-block:: python

   # src/socm/enactor/my_enactor.py
   from typing import List
   import networkx as nx
   from socm.enactor.base import BaseEnactor
   from socm.planner.base import PlanEntry

   class MyCustomEnactor(BaseEnactor):
       """Custom execution backend."""

       def __init__(self, config: Dict):
           super().__init__()
           self.config = config
           self.jobs = {}

       def submit_workflows(
           self,
           plan: List[PlanEntry],
           dag: nx.DiGraph
       ) -> None:
           """Submit workflows to execution backend.

           Args:
               plan: Execution plan from planner
               dag: Workflow dependency graph
           """
           for entry in plan:
               job_id = self._submit_job(entry)
               self.jobs[entry.workflow.name] = {
                   'job_id': job_id,
                   'entry': entry,
                   'state': 'SUBMITTED'
               }
               self._trigger_callbacks('SUBMITTED', entry.workflow)

       def _submit_job(self, entry: PlanEntry) -> str:
           """Submit single job to backend.

           Returns:
               Job ID from backend
           """
           # Your submission logic here
           # Example: Submit to custom scheduler
           job_script = self._create_job_script(entry)
           job_id = self._execute_submission(job_script)
           return job_id

       def _create_job_script(self, entry: PlanEntry) -> str:
           """Generate job submission script."""
           workflow = entry.workflow
           script = f"""#!/bin/bash
   #SBATCH --nodes={entry.resource_range[1] - entry.resource_range[0]}
   #SBATCH --ntasks={workflow.resources['ranks']}
   #SBATCH --cpus-per-task={workflow.resources['threads']}
   #SBATCH --mem={workflow.resources['memory']}MB
   #SBATCH --time={entry.end_time - entry.start_time}
   #SBATCH --qos={entry.qos}

   {workflow.get_command()} {workflow.get_arguments()}
   """
           return script

       def monitor(self) -> None:
           """Monitor job execution and update states."""
           while self._has_active_jobs():
               for wf_name, job_info in self.jobs.items():
                   state = self._check_job_state(job_info['job_id'])

                   if state != job_info['state']:
                       job_info['state'] = state
                       self._trigger_callbacks(state, job_info['entry'].workflow)

               time.sleep(30)  # Poll every 30 seconds

       def _has_active_jobs(self) -> bool:
           """Check if any jobs are still active."""
           active_states = {'SUBMITTED', 'RUNNING'}
           return any(
               job['state'] in active_states
               for job in self.jobs.values()
           )

       def _check_job_state(self, job_id: str) -> str:
           """Query backend for job state."""
           # Your state checking logic
           # Example: Parse squeue output
           pass

Resource Prediction and Slurmise Integration
---------------------------------------------

Advanced Resource Estimation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Slurmise uses machine learning to predict resource requirements:

**Configuring Slurmise**

Create or modify ``src/socm/configs/slurmise.toml``:

.. code-block:: toml

   [slurmise]
   # Model configuration
   model_type = "random_forest"
   model_path = "/path/to/trained/model.pkl"

   # Feature engineering
   numeric_features = ["data_size", "num_observations", "num_detectors"]
   categorical_features = ["band", "site", "wafer"]

   # Prediction targets
   targets = ["walltime", "memory", "cpu_efficiency"]

   # Training data
   training_data_path = "/path/to/historical/jobs.csv"

**Using Slurmise Predictions**

In your workflow or planner:

.. code-block:: python

   from slurmise import ResourcePredictor

   # Initialize predictor
   predictor = ResourcePredictor.from_config("configs/slurmise.toml")

   # Prepare feature vector
   features = {
       'data_size': workflow.data_size_gb,
       'num_observations': workflow.num_obs,
       'band': workflow.bands,
       'site': workflow.site,
   }

   # Get predictions
   predictions = predictor.predict(features)

   # Use predictions
   estimated_walltime = predictions['walltime']  # seconds
   estimated_memory = predictions['memory']  # MB
   estimated_cores = predictions['cpu_cores']

**Training Slurmise Models**

Train custom models on your historical job data:

.. code-block:: python

   from slurmise import ModelTrainer

   # Load training data
   trainer = ModelTrainer(
       data_path="historical_jobs.csv",
       features=["data_size", "num_obs", "band"],
       target="walltime"
   )

   # Train model
   model = trainer.train(algorithm="random_forest")

   # Evaluate
   metrics = trainer.evaluate(model)
   print(f"R² score: {metrics['r2']}")
   print(f"RMSE: {metrics['rmse']}")

   # Save model
   trainer.save_model(model, "walltime_predictor.pkl")

Multi-Campaign Orchestration
-----------------------------

Running Dependent Campaigns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Orchestrate multiple campaigns with dependencies:

.. code-block:: python

   from socm.bookkeeper import Bookkeeper
   from socm.core import Campaign

   # Campaign 1: Preprocessing
   preprocess_campaign = Campaign(
       id=1,
       workflows=preprocessing_workflows,
       campaign_policy="time",
       deadline=120  # 2 hours
   )

   # Campaign 2: Mapmaking (depends on preprocessing)
   mapmaking_campaign = Campaign(
       id=2,
       workflows=mapmaking_workflows,
       campaign_policy="time",
       deadline=480  # 8 hours
   )

   # Campaign 3: Analysis (depends on mapmaking)
   analysis_campaign = Campaign(
       id=3,
       workflows=analysis_workflows,
       campaign_policy="time",
       deadline=240  # 4 hours
   )

   # Execute in sequence
   campaigns = [
       preprocess_campaign,
       mapmaking_campaign,
       analysis_campaign
   ]

   for campaign in campaigns:
       bookkeeper = Bookkeeper(
           campaign=campaign,
           resources=resources,
           policy="time",
           target_resource="tiger3"
       )
       bookkeeper.run()

       # Wait for completion
       bookkeeper.wait_for_completion()

       # Verify success before proceeding
       if not bookkeeper.is_successful():
           print(f"Campaign {campaign.id} failed, aborting...")
           break

Performance Optimization
------------------------

Profiling and Benchmarking
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use RADICAL-Utils profiling:

.. code-block:: python

   import radical.utils as ru

   # Enable profiling
   profiler = ru.Profiler(name='campaign_profiler')

   # Profile sections
   with profiler.timed_block('planning'):
       plan, dag = planner.plan(campaign, resources)

   with profiler.timed_block('execution'):
       enactor.submit_workflows(plan, dag)

   # Generate report
   profiler.report()

**Output:**

.. code-block:: text

   Profiling Report:
   -----------------
   planning:    12.3s (15%)
   execution:   68.7s (85%)
   Total:       81.0s

Memory-Efficient Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For large campaigns, use generators:

.. code-block:: python

   def workflow_generator(config):
       """Generate workflows on-the-fly instead of creating all upfront."""
       for entry in config['entries']:
           yield MyWorkflow(**entry)

   # Use generator
   workflows = list(workflow_generator(config))
   campaign = Campaign(id=1, workflows=workflows, campaign_policy="time")

Caching and Reuse
~~~~~~~~~~~~~~~~~

Cache resource estimates:

.. code-block:: python

   from functools import lru_cache

   class CachedWorkflow(Workflow):
       @lru_cache(maxsize=128)
       def estimate_resources(self, data_size: float) -> Dict:
           # Expensive computation
           return self._compute_resources(data_size)

Advanced Configuration Techniques
----------------------------------

Template-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use Jinja2 templates for dynamic configuration:

**template.toml.j2:**

.. code-block:: jinja

   [campaign]
   deadline = "{{ deadline }}"
   resource = "{{ resource }}"

   {% for band in bands %}
   [campaign.ml-mapmaking-{{ band }}]
   context = "{{ context }}"
   bands = "{{ band }}"
   output_dir = "{{ output_dir }}/{{ band }}"
   {% endfor %}

**Generate configuration:**

.. code-block:: python

   from jinja2 import Template

   with open('template.toml.j2') as f:
       template = Template(f.read())

   config = template.render(
       deadline="8h",
       resource="tiger3",
       bands=["f090", "f150", "f220"],
       context="/path/to/context.yaml",
       output_dir="/path/to/output"
   )

   with open('campaign.toml', 'w') as f:
       f.write(config)

Environment-Specific Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Support multiple environments:

.. code-block:: toml

   # base_config.toml
   [campaign]
   deadline = "8h"

   # development.toml (inherits from base)
   [campaign]
   resource = "tiger3"
   execution_schema = "local"

   # production.toml (inherits from base)
   [campaign]
   resource = "tiger3"
   execution_schema = "remote"

**Load with override:**

.. code-block:: python

   import toml

   base = toml.load('base_config.toml')
   env = toml.load(f'{environment}.toml')

   # Merge configurations
   config = {**base, **env}

Integration with Other Tools
-----------------------------

Integration with Workflow Management Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Using with Nextflow:**

.. code-block:: groovy

   // nextflow.nf
   process runCampaign {
       input:
       path config

       output:
       path 'output/*'

       script:
       """
       socm -t ${config}
       """
   }

   workflow {
       config_ch = Channel.fromPath('campaign.toml')
       runCampaign(config_ch)
   }

**Using with Snakemake:**

.. code-block:: python

   # Snakefile
   rule campaign:
       input:
           config="campaign.toml"
       output:
           directory("output")
       shell:
           "socm -t {input.config}"

Custom Callbacks and Hooks
---------------------------

Implementing Custom Callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom logic on workflow state changes:

.. code-block:: python

   from socm.enactor.base import BaseEnactor

   class NotificationEnactor(BaseEnactor):
       def __init__(self, email_config):
           super().__init__()
           self.email_config = email_config

           # Register custom callbacks
           self.register_callback('COMPLETED', self._on_workflow_completed)
           self.register_callback('FAILED', self._on_workflow_failed)

       def _on_workflow_completed(self, workflow):
           """Send notification on completion."""
           self._send_email(
               subject=f"Workflow {workflow.name} completed",
               body=f"Workflow {workflow.name} finished successfully."
           )

       def _on_workflow_failed(self, workflow):
           """Send alert on failure."""
           self._send_email(
               subject=f"ALERT: Workflow {workflow.name} failed",
               body=f"Workflow {workflow.name} encountered an error.",
               priority="high"
           )

       def _send_email(self, subject, body, priority="normal"):
           # Email sending logic
           pass

Distributed Campaign Management
--------------------------------

Running Campaigns Across Multiple Sites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manage campaigns across different HPC systems:

.. code-block:: python

   from socm.bookkeeper import Bookkeeper
   from socm.resources import TigerResource, CustomResource

   # Define multiple resources
   resources = {
       "tiger3": TigerResource(),
       "custom_hpc": CustomResource(
           name="custom",
           nodes=200,
           cores_per_node=64,
           memory_per_node=256000
       )
   }

   # Partition workflows by resource
   tiger_workflows = [wf for wf in workflows if wf.preferred_resource == "tiger3"]
   custom_workflows = [wf for wf in workflows if wf.preferred_resource == "custom"]

   # Run on both resources
   for resource_name, wf_list in [("tiger3", tiger_workflows),
                                   ("custom", custom_workflows)]:
       if wf_list:
           campaign = Campaign(workflows=wf_list)
           bookkeeper = Bookkeeper(
               campaign=campaign,
               resources={resource_name: resources[resource_name]},
               target_resource=resource_name
           )
           bookkeeper.run()

Best Practices for Advanced Usage
----------------------------------

1. **Modular Design**: Keep workflows, planners, and enactors modular
2. **Comprehensive Testing**: Test custom components thoroughly
3. **Logging**: Add detailed logging for debugging
4. **Documentation**: Document custom components with docstrings
5. **Version Control**: Track configuration changes in git
6. **Monitoring**: Implement monitoring for production campaigns
7. **Error Handling**: Handle edge cases gracefully
8. **Performance**: Profile and optimize bottlenecks
9. **Validation**: Validate inputs early and fail fast
10. **Reproducibility**: Ensure campaigns are reproducible

Conclusion
----------

These advanced features enable you to:

* Create custom workflows for specialized tasks
* Implement custom scheduling algorithms
* Integrate with other tools and systems
* Optimize performance and resource usage
* Scale to complex multi-campaign orchestration

For more information, see:

* :doc:`architecture` for system internals
* :doc:`api_complete` for complete API reference
* :doc:`developer_guide` for contributing guidelines
