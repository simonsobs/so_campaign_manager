SO Campaign Manager Documentation
===================================

SO Campaign Manager (``socm``) plans and runs Simons Observatory analysis campaigns on SLURM clusters: ML mapmaking and null tests, power spectra, and LAT simulations.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   installation
   quickstart
   tutorial

.. toctree::
   :maxdepth: 2
   :caption: User Documentation:

   campaigns
   user_guide
   workflows
   resources
   faq

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics:

   architecture
   advanced_topics

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api
   api_complete

.. toctree::
   :maxdepth: 2
   :caption: Development:

   developer_guide

What is SO Campaign Manager?
----------------------------

You describe a campaign, a set of workflows and a deadline, in one configuration file. socm plans the workflows to finish within the deadline, picks the SLURM QoS and core count, submits them through RADICAL-Pilot, and follows them until they finish.

Key Features
------------

* **Intelligent Scheduling**: Uses HEFT (Heterogeneous Earliest Finish Time) algorithm to optimize workflow execution
* **Campaign Management**: Organize and execute multiple workflows with deadline-based policies
* **Resource Management**: Automatic resource allocation and QoS selection for SLURM
* **Workflow Support**: Built-in support for ML mapmaking, null tests, power spectra, and LAT and SAT simulations
* **SLURM Integration**: Seamless job submission and monitoring via RADICAL-Pilot
* **Flexible Configuration**: TOML for mapmaking campaigns; YAML stage DAGs for power spectra and LAT simulations, with stage matrices for LAT simulations
* **Extensible Architecture**: Easy to add custom workflows, planners, and execution backends
* **Resource History**: Records the runtime and memory of every successful workflow in Slurmise, for future resource prediction
* **Dependency Management**: Workflows start when their dependencies finish; a failure stops their dependents

Use Cases
---------

SO Campaign Manager is designed for:

* **Mapmaking Campaigns**: Process large volumes of time-ordered data into maps
* **Null Test Validation**: Run comprehensive null test suites for systematic error detection
* **Simulation Campaigns**: Generate schedules and run LAT simulations for every split, band and tube
* **Power Spectra Pipelines**: Run PSpipe scripts as a dependency graph
* **Multi-Band Analysis**: Coordinate processing across multiple frequency bands
* **Resource-Constrained Execution**: Optimize resource usage within budget constraints
* **Long-Running Campaigns**: Manage campaigns spanning days or weeks

Quick Navigation
----------------

**New Users:**

* :doc:`installation` - Install the package and dependencies
* :doc:`quickstart` - Get up and running in 5 minutes
* :doc:`tutorial` - Step-by-step tutorials for common tasks

**Regular Users:**

* :doc:`campaigns` - How to create each type of campaign, with complete examples
* :doc:`user_guide` - Running campaigns: command line, logs, failures, troubleshooting
* :doc:`workflows` - Available workflows and their configuration
* :doc:`resources` - Supported HPC systems and QoS policies
* :doc:`faq` - Frequently asked questions and troubleshooting

**Advanced Users:**

* :doc:`architecture` - System architecture and design
* :doc:`advanced_topics` - Custom workflows, planners, and advanced features
* :doc:`api` - Public API reference

**Developers:**

* :doc:`developer_guide` - Contributing and development setup
* :doc:`api_complete` - Complete API reference (including internals)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
