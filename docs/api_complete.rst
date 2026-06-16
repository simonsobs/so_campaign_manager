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

Resources
---------

.. automodule:: socm.resources.tiger
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.resources.perlmutter
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

.. automodule:: socm.resources.universe
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Workflows
---------

ML Mapmaking
~~~~~~~~~~~~

.. automodule:: socm.workflows.ml_mapmaking
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Power Spectra
~~~~~~~~~~~~~

.. automodule:: socm.workflows.spectra
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

SAT Simulation
~~~~~~~~~~~~~~

.. automodule:: socm.workflows.sat_simulation
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Null Tests
~~~~~~~~~~

Base Null Test
^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.base
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Mission (Time) Null Test
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.time_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Wafer Null Test
^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.wafer_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Direction Null Test
^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.direction_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

PWV Null Test
^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.pwv_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Day/Night Null Test
^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.day_night_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Moon Rise/Set Null Test
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.moonrise_set_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Elevation Null Test
^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.elevation_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Sun Close/Far Null Test
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.sun_close_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Moon Close/Far Null Test
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.moon_close_null_test
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:

Smart Split Null Test
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: socm.workflows.ml_null_tests.smart_split_null_test
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
