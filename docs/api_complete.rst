Complete API Reference
======================

This section provides comprehensive API documentation including all methods, including private and internal methods that may be useful for developers extending the codebase.

.. note::
   This section includes private methods (starting with `_`) that are implementation details.
   These may change between versions without notice. For stable public API, see :doc:`api`.

Core Modules
------------

Models
~~~~~~

.. automodule:: socm.core.models
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Campaign Management
-------------------

Bookkeeper
~~~~~~~~~~

.. automodule:: socm.bookkeeper.bookkeeper
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Planning
~~~~~~~~

.. automodule:: socm.planner.base
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.planner.heft_planner
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Execution
---------

Enactors
~~~~~~~~

.. automodule:: socm.enactor.base
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.enactor.rp_enactor
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Workflows
~~~~~~~~~

Base Workflow
^^^^^^^^^^^^^

.. automodule:: socm.workflows
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

ML Mapmaking
^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_mapmaking
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

SAT Simulation
^^^^^^^^^^^^^^

.. automodule:: socm.workflows.sat_simulation
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Null Tests
^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.base
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.workflows.ml_null_tests.time_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.workflows.ml_null_tests.wafer_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.workflows.ml_null_tests.pwv_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.workflows.ml_null_tests.direction_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

.. automodule:: socm.utils.misc
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.utils.states
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Command Line Interface
----------------------

.. automodule:: socm.__main__
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
