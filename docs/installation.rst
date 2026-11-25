Installation
============

Requirements
------------

* Python 3.11 or 3.12
* Linux, with access to a SLURM cluster to run campaigns. RADICAL-Pilot and Slurmise
  are not installed on macOS, so campaigns cannot run there.

Install
-------

With pip:

.. code-block:: bash

   pip install so_campaign_manager

ML mapmaking and null-test campaigns also need ``sotodlib`` and ``astral``, which come
with the ``mapmaking`` extra:

.. code-block:: bash

   pip install "so_campaign_manager[mapmaking]"

Without it, ``socm lat-mapmaking`` cannot create those workflows; power spectra and
LAT simulation campaigns work either way.

From Source
-----------

.. code-block:: bash

   git clone https://github.com/simonsobs/so_campaign_manager.git
   cd so_campaign_manager
   uv sync --extra mapmaking

   # With the test, lint and documentation tools as well:
   uv sync --extra mapmaking --group dev --group docs

Verify
------

.. code-block:: bash

   socm --help

This lists the three campaign commands: ``lat-mapmaking``, ``spectra`` and ``lat-sims``.

Main Dependencies
-----------------

* **radical.pilot**: submits and runs the workflows on SLURM
* **slurmise**: records workflow runtimes and memory for resource prediction
* **pydantic**: validates configurations and workflows
* **networkx**: workflow dependency graphs
* **toml**, **humanfriendly**: configuration parsing, sizes and durations
* **loguru**: logging
