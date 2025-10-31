SO Campaign Manager Documentation
===================================

Welcome to the SO Campaign Manager documentation! This package provides a comprehensive workflow orchestration system for managing and executing mapmaking campaigns on high-performance computing resources, specifically designed for the Simons Observatory project.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   installation
   quickstart
   tutorial

.. toctree::
   :maxdepth: 2
   :caption: User Documentation:

   user_guide
   workflows
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

SO Campaign Manager is a sophisticated workflow orchestration system that enables efficient execution of mapmaking campaigns on HPC clusters. It combines intelligent scheduling, resource optimization, and seamless SLURM integration to maximize throughput while meeting campaign deadlines.

Key Features
------------

* **Intelligent Scheduling**: Uses HEFT (Heterogeneous Earliest Finish Time) algorithm to optimize workflow execution
* **Campaign Management**: Organize and execute multiple workflows with deadline-based policies
* **Resource Management**: Automatic resource allocation and QoS selection for SLURM
* **Workflow Support**: Built-in support for ML mapmaking, null tests, and SAT simulations
* **SLURM Integration**: Seamless job submission and monitoring via RADICAL-Pilot
* **Flexible Configuration**: TOML-based hierarchical configuration system
* **Extensible Architecture**: Easy to add custom workflows, planners, and execution backends
* **Resource Prediction**: ML-based resource estimation via Slurmise integration
* **Dependency Management**: Automatic workflow dependency resolution

Use Cases
---------

SO Campaign Manager is designed for:

* **Mapmaking Campaigns**: Process large volumes of time-ordered data into maps
* **Null Test Validation**: Run comprehensive null test suites for systematic error detection
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

* :doc:`user_guide` - Comprehensive reference for all features
* :doc:`workflows` - Available workflows and their configuration
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