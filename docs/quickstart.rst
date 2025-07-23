Quick Start
===========

This guide will help you get up and running with SO Campaign Manager quickly.

Basic Workflow
--------------

1. **Create a configuration file** - Define your campaign in a TOML file
2. **Run the campaign** - Execute using the command-line interface
3. **Monitor progress** - Track execution and results

Example Configuration
---------------------

Create a file called ``campaign.toml``:

.. code-block:: toml

   [campaign]
   deadline = "2d"

   [campaign.resources]
   nodes = 4
   cores-per-node = 112

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
   memory = "80000"  # in MBs
   runtime = "80000" # in seconds

   [campaign.ml-mapmaking.environment]
   MOBY2_TOD_STAGING_PATH = "/tmp/"
   DOT_MOBY2 = "/path/to/act_dot_moby2"
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

Running Your First Campaign
---------------------------

Execute your campaign with:

.. code-block:: bash

   socm -t campaign.toml

This will:

1. Parse your configuration
2. Create the required workflows
3. Set up the computing resources
4. Submit jobs to SLURM
5. Monitor execution

Understanding the Output
------------------------

The campaign manager will:

* Create output directories as specified in your configuration
* Log execution details
* Generate maps and analysis products based on your workflows

Next Steps
----------

* Read the :doc:`user_guide` for detailed configuration options
* Explore :doc:`workflows` to understand available workflow types
* Check the :doc:`api` for programmatic usage

Simple Python Example
----------------------

You can also use SO Campaign Manager programmatically:

.. code-block:: python

   from socm.bookkeeper import Bookkeeper
   from socm.core import Campaign, Resource
   from socm.workflows import MLMapmakingWorkflow

   # Create workflows
   workflow = MLMapmakingWorkflow(
       name="test_workflow",
       executable="so-site-pipeline",
       subcommand="make-filterbin-map",
       context="path/to/context.yaml",
       # ... other parameters
   )

   # Create campaign
   campaign = Campaign(
       id=1,
       workflows=[workflow],
       campaign_policy="time"
   )

   # Define resource
   resource = Resource(
       name="tiger3",
       nodes=4,
       cores_per_node=112,
       memory_per_node=100000000,
       default_queue="tiger-test"
   )

   # Execute
   bookkeeper = Bookkeeper(
       campaign=campaign,
       resources={"tiger3": resource},
       policy="time",
       target_resource="tiger3"
   )
   
   bookkeeper.run()