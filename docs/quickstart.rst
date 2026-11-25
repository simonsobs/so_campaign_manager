Quick Start
===========

This guide will help you get up and running with SO Campaign Manager quickly.

Basic Workflow
--------------

1. **Pick the campaign type** - mapmaking, power spectra or LAT simulations
2. **Create a configuration file** - TOML for mapmaking, YAML for the other two
3. **Check it with a dry run** - plan the campaign without submitting anything
4. **Run the campaign** - socm submits it to SLURM and watches it until it ends

Each campaign type has its own ``socm`` subcommand:

.. code-block:: bash

   socm lat-mapmaking -t campaign.toml   # ML mapmaking and null tests
   socm spectra -y campaign.yml          # PSpipe power spectra
   socm lat-sims -y campaign.yml         # LAT simulations

Example Configuration
---------------------

Create a file called ``campaign.toml`` for a single ML mapmaking run:

.. code-block:: toml

   [campaign]
   deadline = "2d"
   resource = "tiger3"
   execution_schema = "remote"
   requested_resources = 448

   [campaign.ml-mapmaking]
   context = "file:///path/to/context.yaml"
   area = "file:///path/to/area.fits"
   preprocess_config = "file:///path/to/preprocess.yaml"
   output_dir = "/path/to/output"
   bands = "f090"
   comps = "TQU"
   maxiter = 10
   query = "obs_id='1575600533.1575611468.ar5_1'"
   tiled = 1
   site = "so_lat"

   [campaign.ml-mapmaking.resources]
   ranks = 1
   threads = 32
   memory = "80G"     # a size with a unit; a bare number is bytes
   runtime = "22h"    # a duration; a bare number is seconds

   [campaign.ml-mapmaking.environment]
   MOBY2_TOD_STAGING_PATH = "/tmp/"
   DOT_MOBY2 = "/path/to/act_dot_moby2"
   SOTODLIB_SITECONFIG = "/path/to/site.yaml"

Running Your First Campaign
---------------------------

Check the configuration with a dry run first, then run it:

.. code-block:: bash

   socm lat-mapmaking -t campaign.toml --dry-run
   socm lat-mapmaking -t campaign.toml

This will:

1. Parse your configuration
2. Create the required workflows
3. Plan them within the deadline and pick the SLURM QoS
4. Submit them to SLURM through RADICAL-Pilot
5. Monitor execution until every workflow has finished, or one has failed

Understanding the Output
------------------------

The campaign manager will:

* Create output directories as specified in your configuration
* Write its logs to a session directory in the directory you ran ``socm`` from
* Generate maps and analysis products based on your workflows

The terminal only shows warnings and errors. Set ``SOCM_LOG_LEVEL=INFO`` to follow
progress there too.

Next Steps
----------

* Read :doc:`campaigns` for a complete example of every campaign type
* Read the :doc:`user_guide` for detailed configuration options
* Explore :doc:`workflows` to understand available workflow types
