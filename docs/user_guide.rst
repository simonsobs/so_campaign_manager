User Guide
==========

This comprehensive guide covers all aspects of using SO Campaign Manager.

Configuration System
---------------------

SO Campaign Manager uses TOML configuration files to define campaigns. The configuration is structured in several sections:

Campaign Section
~~~~~~~~~~~~~~~~

The main campaign section defines global settings:

.. code-block:: toml

   [campaign]
   deadline = "2d"  # Campaign deadline (supports: "1d", "2h", "30m", etc.)

   [campaign.resources]
   nodes = 4              # Number of compute nodes
   cores-per-node = 112   # CPU cores per node

Workflow Sections
~~~~~~~~~~~~~~~~~

Each workflow type has its own section. Currently supported workflows:

* ``ml-mapmaking`` - Maximum likelihood mapmaking
* ``ml-null-tests`` - Null test analysis

Example ML Mapmaking Configuration:

.. code-block:: toml

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   output_dir = "/path/to/output"
   bands = "f090"
   wafer = "ws0"
   comps = "TQU"
   maxiter = 10
   query = "obs_id='1575600533.1575611468.ar5_1'"
   tiled = 1
   site = "act"

   [campaign.ml-mapmaking.resources]
   ranks = 1
   threads = 32
   memory = "80000"  # Memory in MB
   runtime = "80000" # Runtime in seconds

   [campaign.ml-mapmaking.environment]
   MOBY2_TOD_STAGING_PATH = "/tmp/"
   DOT_MOBY2 = "/path/to/act_dot_moby2"
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

Resource Management
-------------------

Computing Resources
~~~~~~~~~~~~~~~~~~~

Define the target computing resource:

.. code-block:: python

   resource = Resource(
       name="tiger3",                # Resource identifier
       nodes=4,                      # Available nodes
       cores_per_node=112,           # Cores per node
       memory_per_node=100000000,    # Memory per node (bytes)
       default_queue="tiger-test",   # SLURM queue
       maximum_walltime=3600000      # Max walltime (seconds)
   )

Resource Allocation
~~~~~~~~~~~~~~~~~~~

Each workflow can specify its resource requirements:

* **ranks**: Number of MPI ranks
* **threads**: Number of OpenMP threads
* **memory**: Memory requirement (MB)
* **runtime**: Expected runtime (seconds)

The campaign manager automatically:

1. Calculates total resource needs
2. Optimizes job allocation
3. Submits to appropriate SLURM queues

Workflow Types
--------------

ML Mapmaking Workflow
~~~~~~~~~~~~~~~~~~~~~

Maximum likelihood mapmaking for creating maps from time-ordered data.

**Required Parameters:**

* ``context``: Path to context file
* ``area``: Path to area definition file
* ``output_dir``: Output directory
* ``bands``: Frequency bands (e.g., "f090", "f150")
* ``wafer``: Wafer identifier
* ``comps``: Components to map ("T", "TQU", etc.)
* ``query``: Data selection query

**Optional Parameters:**

* ``maxiter``: Maximum iterations (default: 100)
* ``tiled``: Use tiled processing (0 or 1)
* ``site``: Observatory site

ML Null Tests Workflow
~~~~~~~~~~~~~~~~~~~~~~~

Statistical null tests for validating mapmaking results.

**Mission Tests:**

.. code-block:: toml

   [campaign.ml-null-tests.mission-tests]
   chunk_nobs = 10  # Chunk size in days
   nsplits = 8      # Number of splits (must be multiple of 2)

**Wafer Tests:**

.. code-block:: toml

   [campaign.ml-null-tests.wafer-tests]
   chunk_nobs = 10  # Chunk size in days
   nsplits = 8      # Number of splits

Campaign Policies
-----------------

Time Policy
~~~~~~~~~~~

The "time" policy minimizes total campaign completion time by:

1. Analyzing workflow dependencies
2. Optimizing parallel execution
3. Balancing resource utilization

Currently, "time" is the only supported policy, but the architecture supports adding new policies.

Environment Variables
---------------------

Common environment variables for SO workflows:

* ``MOBY2_TOD_STAGING_PATH``: Temporary storage path
* ``DOT_MOBY2``: Moby2 configuration directory
* ``SOTODLIB_SITECONFIG``: Site configuration file

Command Line Interface
----------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   socm -t /path/to/campaign.toml

Options
~~~~~~~

* ``-t, --toml``: Path to configuration file (required)

The CLI automatically:

1. Validates configuration
2. Creates workflow instances
3. Sets up resources
4. Executes the campaign

Monitoring and Logging
----------------------

The campaign manager provides detailed logging of:

* Configuration validation
* Workflow creation
* Resource allocation
* Job submission
* Execution progress
* Error handling

Logs are written to stdout and can be redirected as needed.

Best Practices
--------------

Configuration
~~~~~~~~~~~~~

1. **Use absolute paths** for all file references
2. **Test configurations** with small datasets first
3. **Set realistic deadlines** based on data volume
4. **Monitor resource usage** to optimize future runs

Resource Management
~~~~~~~~~~~~~~~~~~~

1. **Right-size resources** - don't over-allocate
2. **Consider queue limits** when setting runtime
3. **Use appropriate memory estimates** to avoid OOM errors
4. **Test on development queues** before production runs

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Configuration Errors:**
   Check TOML syntax and required parameters

**Resource Allocation Failures:**
   Verify SLURM queue availability and limits

**Workflow Execution Errors:**
   Check environment variables and file paths

**Out of Memory Errors:**
   Increase memory allocation or reduce data chunk size

Getting Help
~~~~~~~~~~~~

* Check this documentation for configuration examples
* Review example configurations in the ``examples/`` directory
* Examine log output for specific error messages
* File issues on the GitHub repository for bugs or feature requests
