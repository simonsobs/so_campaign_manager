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

The planner evaluates these limits at scheduling time and selects the smallest QoS tier
that satisfies each workflow's walltime and core requirements.

Specifying a Resource in Configuration
--------------------------------------

TOML campaigns
~~~~~~~~~~~~~~

Set the target resource and the number of nodes to request in the ``[campaign]`` and
``[campaign.resources]`` sections:

.. code-block:: toml

   [campaign]
   deadline = "2d"
   resource = "tiger3"

   [campaign.resources]
   nodes = 4
   cores-per-node = 112

DAG YAML campaigns
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   campaign:
     deadline: 24h
     resource: tiger3
     requested_resources: 3359   # total cores requested

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

Register the resource name so it can be referenced from configuration files by passing
the instance directly to ``Bookkeeper``.
