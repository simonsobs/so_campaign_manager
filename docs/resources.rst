Resources
=========

SO Campaign Manager models HPC systems as ``Resource`` objects that capture node counts,
core layout, memory, and SLURM Quality of Service (QoS) policies. The planner uses this
information to schedule workflows into the right QoS tier automatically.

Core Concepts
-------------

Resource
~~~~~~~~

A ``Resource`` describes the physical characteristics of an HPC system:

* ``name``: Identifier used to select the resource in configuration files
* ``nodes``: Total number of compute nodes available
* ``cores_per_node``: CPU cores per node
* ``memory_per_node``: Memory per node in MB
* ``qos``: List of :ref:`QoS policies <qos-policies>` available on the system

.. _qos-policies:

QoS Policy
~~~~~~~~~~

A ``QosPolicy`` maps to a SLURM QoS tier and defines its limits:

* ``name``: QoS name as known to SLURM (e.g. ``short``, ``regular``)
* ``max_walltime``: Maximum walltime in **minutes** (``None`` = unlimited)
* ``max_jobs``: Maximum number of concurrent jobs (``None`` = unlimited)
* ``max_cores``: Maximum total cores that can be requested at once (``None`` = unlimited)

With ``execution_schema = "remote"``, the planner chooses one QoS tier for the
campaign. If a tier allows the cores the campaign needs for its whole deadline, the
campaign runs as one pilot job in that tier. Otherwise it is split into several
pilot jobs that run one after another, in the tier with the longest walltime that
still allows those cores.

Specifying a Resource in Configuration
--------------------------------------

Every campaign names its resource in the ``campaign`` section, together with the
number of cores it may request:

.. code-block:: toml

   [campaign]
   deadline = "2d"
   resource = "tiger3"           # tiger3 (default), perlmutter, universe or localhost
   execution_schema = "remote"
   requested_resources = 3360    # cores

In YAML campaigns the same keys go under ``campaign:``. With ``execution_schema =
"remote"`` the planner picks the core count, up to ``requested_resources``, and the
QoS tier; with ``"batch"`` it requests exactly ``requested_resources`` cores. See
:doc:`campaigns`.

Supported Resources
-------------------

Tiger 3 (Princeton)
~~~~~~~~~~~~~~~~~~~

The primary SO mapmaking resource. Pre-configured as ``TigerResource``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 20

   * - Property
     - Value
     - Unit
   * - Nodes
     - 492
     -
   * - Cores per node
     - 112
     -
   * - Memory per node
     - 1 000 000
     - MB

**QoS tiers:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20

   * - QoS
     - Max walltime
     - Max jobs
     - Max cores
   * - ``test``
     - 1 h
     - 1
     - 8 000
   * - ``vshort``
     - 5 h
     - 2 000
     - 55 104
   * - ``short``
     - 24 h
     - 50
     - 8 000
   * - ``medium``
     - 3 d
     - 80
     - 4 000
   * - ``long``
     - 6 d
     - 16
     - 1 000
   * - ``vlong``
     - 15 d
     - 8
     - 900

Perlmutter (NERSC)
~~~~~~~~~~~~~~~~~~

NERSC Perlmutter system. Pre-configured as ``PerlmutterResource``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 20

   * - Property
     - Value
     - Unit
   * - Nodes
     - 3 072
     -
   * - Cores per node
     - 128
     -
   * - Memory per node
     - 1 000 000
     - MB

**QoS tiers:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20

   * - QoS
     - Max walltime
     - Max jobs
     - Max cores
   * - ``regular``
     - 48 h
     - 5 000
     - 393 216
   * - ``interactive``
     - 4 h
     - 2
     - 512
   * - ``shared_interactive``
     - 4 h
     - 2
     - 64
   * - ``debug``
     - 30 min
     - 5
     - 1 024

Universe
~~~~~~~~

Princeton Universe cluster. Pre-configured as ``UniverseResource``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 20

   * - Property
     - Value
     - Unit
   * - Nodes
     - 28
     -
   * - Cores per node
     - 224
     -
   * - Memory per node
     - 1 000 000
     - MB

**QoS tiers:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20

   * - QoS
     - Max walltime
     - Max jobs
     - Max cores
   * - ``main``
     - 30 d
     - 5 000
     - 6 272

Localhost
~~~~~~~~~

The machine socm runs on, for testing. Pre-configured as ``LocalResource`` with 1 node
of 8 cores and 64 000 MB, and one QoS tier, ``default``: 100 h walltime, 1 job, and
all 8 cores.

Adding a Custom Resource
------------------------

To define a new HPC system, subclass ``Resource`` and provide the QoS policies in
``__init__``:

.. code-block:: python

   from socm.core import QosPolicy, Resource

   class MyClusterResource(Resource):
       name: str = "mycluster"
       nodes: int = 100
       cores_per_node: int = 64
       memory_per_node: int = 512000  # MB

       def __init__(self, **data):
           super().__init__(**data)
           self.qos = [
               QosPolicy(name="short", max_walltime=1440, max_jobs=100, max_cores=6400),
               QosPolicy(name="long",  max_walltime=10080, max_jobs=20, max_cores=3200),
           ]

Then add the class to ``registered_resources`` in ``socm/resources/__init__.py`` under
its name, so a campaign can select it with ``resource = "mycluster"``.
