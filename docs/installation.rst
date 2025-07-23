Installation
============

Requirements
------------

* Python 3.11+
* Access to a SLURM-based computing cluster (for execution)

Basic Installation
------------------

Install SO Campaign Manager using pip:

.. code-block:: bash

   pip install so_campaign_manager

Development Installation
------------------------

For development or to get the latest features, install from source:

.. code-block:: bash

   git clone https://github.com/simonsobs/so_campaign_manager.git
   cd so_campaign_manager
   pip install -e .

Development Dependencies
------------------------

To install development dependencies for testing and documentation:

.. code-block:: bash

   pip install -e ".[dev]"

This installs additional packages needed for:

* Code formatting and linting (ruff, darker, flake8)
* Testing (pytest, hypothesis)
* Coverage reporting (pytest-cov, coveralls)

Verification
------------

Verify your installation by running:

.. code-block:: bash

   socm --help

You should see the help message for the SO Campaign Manager command-line interface.

Dependencies
------------

Core dependencies include:

* **pydantic** (≥2.0) - Data validation and settings management
* **numpy** - Numerical computing
* **radical.pilot** - Workflow execution engine
* **networkx** - Graph algorithms for workflow dependencies
* **toml** - Configuration file parsing
* **click** - Command-line interface
* **sotodlib** - SO-specific data handling
* **slurmise** - SLURM job management

These dependencies are automatically installed with the package.