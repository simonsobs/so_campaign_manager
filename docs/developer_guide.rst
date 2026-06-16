Developer Guide
===============

This guide is for developers who want to contribute to SO Campaign Manager or extend its functionality.

Development Setup
-----------------

Environment Setup
~~~~~~~~~~~~~~~~~

1. **Clone the repository:**

.. code-block:: bash

   git clone https://github.com/simonsobs/so_campaign_manager.git
   cd so_campaign_manager

2. **Install development dependencies:**

.. code-block:: bash

   uv sync --group dev

3. **Install pre-commit hooks (optional but recommended):**

.. code-block:: bash

   uv run pre-commit install

Code Style and Quality
----------------------

The project follows strict code quality standards:

PEP8 Compliance (Mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All code must be PEP8 compliant with a maximum line length of 120 characters
(configured in ``pyproject.toml``). Use ruff and flake8 to check:

.. code-block:: bash

   ruff check src/
   uv run flake8 src/socm tests/

Code Formatting (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use ``darker`` for progressive code formatting:

.. code-block:: bash

   # Check what would be changed
   uv run darker --diff -r origin/main src/socm -L flake8

   # Apply formatting
   uv run darker -r origin/main src/socm -L flake8

Project Structure
-----------------

.. code-block::

   so_campaign_manager/
   ├── src/socm/              # Main package
   │   ├── __init__.py
   │   ├── __main__.py        # CLI entry point
   │   ├── core/              # Core models and abstractions
   │   │   ├── __init__.py
   │   │   └── models.py      # Pydantic models
   │   ├── bookkeeper/        # Main execution engine
   │   │   ├── __init__.py
   │   │   └── bookkeeper.py
   │   ├── workflows/         # Workflow implementations
   │   │   ├── __init__.py    # registered_workflows dict + subcampaign_map
   │   │   ├── ml_mapmaking.py
   │   │   ├── sat_simulation.py
   │   │   ├── spectra.py
   │   │   └── ml_null_tests/
   │   │       ├── __init__.py
   │   │       ├── base.py
   │   │       ├── time_null_test.py
   │   │       ├── wafer_null_test.py
   │   │       ├── direction_null_test.py
   │   │       ├── pwv_null_test.py
   │   │       ├── day_night_null_test.py
   │   │       ├── moonrise_set_null_test.py
   │   │       ├── elevation_null_test.py
   │   │       ├── sun_close_null_test.py
   │   │       ├── moon_close_null_test.py
   │   │       └── smart_split_null_test.py
   │   ├── enactor/           # Execution backends
   │   │   ├── __init__.py
   │   │   ├── base.py
   │   │   ├── rp_enactor.py
   │   │   └── dryrun_enactor.py
   │   ├── planner/           # Campaign planning
   │   │   ├── __init__.py
   │   │   ├── base.py
   │   │   └── heft_planner.py
   │   ├── resources/         # HPC resource definitions
   │   │   ├── __init__.py
   │   │   ├── tiger.py
   │   │   ├── perlmutter.py
   │   │   └── universe.py
   │   └── utils/             # Utilities
   │       ├── __init__.py
   │       ├── misc.py
   │       └── states.py
   ├── tests/                 # Test suite
   ├── docs/                  # Documentation
   └── pyproject.toml         # Project configuration

Branching Model
---------------

We use a structured branching model for collaboration:

Branch Types
~~~~~~~~~~~~

* ``main``: Latest stable development (never commit directly)
* ``feature/abc``: Development of new features
* ``fix/abc_123``: Bug fixes (reference GitHub issue)
* ``hotfix/abc_123``: Urgent fixes
* ``tmp/abc``: Temporary branches (will be deleted)
* ``test/abc``: Integration testing branches

Development Workflow
~~~~~~~~~~~~~~~~~~~~

1. **Create feature branch:**

.. code-block:: bash

   git checkout main
   git pull origin main
   git checkout -b feature/my_feature

2. **Develop and test:**

.. code-block:: bash

   # Make changes
   # Run tests
   uv run pytest tests/ --cov
   # Check code style
   ruff check src/
   uv run darker --diff -r origin/main src/ -L flake8

3. **Create pull request:**
   * Target ``main`` branch
   * Include description of changes
   * Reference related issues

4. **Code review and merge**

Branch Policies
~~~~~~~~~~~~~~~

* All branches are short-lived
* Merge ``main`` into your feature branch before creating a PR

Testing
-------

Test Structure
~~~~~~~~~~~~~~

Tests are organized to mirror the package structure:

.. code-block::

   tests/
   ├── __init__.py
   ├── conftest.py            # Test configuration and shared fixtures
   ├── test_bookkeeper.py     # Bookkeeper tests
   ├── test_misc.py           # Utility tests
   ├── test_planner.py        # Planner tests
   └── workflows/             # Workflow tests

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests with coverage
   pytest -vvv tests/ --cov --cov-append

   # Run specific test file
   pytest tests/test_bookkeeper.py

   # Run specific test
   pytest tests/test_core_models.py::test_workflow_creation -v

Writing Tests
~~~~~~~~~~~~~

Follow these guidelines:

1. **Use descriptive test names:**

.. code-block:: python

   def test_campaign_creation_with_valid_workflows():
       """Test that campaigns can be created with valid workflow lists."""

2. **Test edge cases:**

.. code-block:: python

   def test_resource_allocation_with_insufficient_memory():
       """Test resource allocation fails gracefully with insufficient memory."""

3. **Use fixtures for common setup:**

.. code-block:: python

   @pytest.fixture
   def sample_campaign():
       """Create a sample campaign for testing."""
       return Campaign(id=1, workflows=[], campaign_policy="time", deadline="1d")

Adding New Features
-------------------

Workflow Types
~~~~~~~~~~~~~~

To add a new workflow type:

1. **Create workflow class:**

.. code-block:: python

   # src/socm/workflows/my_workflow.py
   from typing import List
   from socm.core.models import Workflow

   class MyWorkflow(Workflow):
       special_param: str

       def get_command(self) -> str:
           return f"{self.executable} {self.subcommand}"

       def get_arguments(self) -> List[str]:
           # get_arguments must return a List[str], not a plain str
           return [f"--special={self.special_param}"]

       @classmethod
       def get_workflows(cls, descriptions):
           if isinstance(descriptions, dict):
               descriptions = [descriptions]
           return [cls(**desc) for desc in descriptions]

.. note::

   ``get_arguments()`` must return a ``List[str]``, **not** a single string.
   The enactor concatenates the list elements when building the RP task
   description, so returning a plain string will cause incorrect argument
   splitting at execution time.

2. **Register workflow:**

.. code-block:: python

   # src/socm/workflows/__init__.py
   from .my_workflow import MyWorkflow  # noqa: F401

   registered_workflows = {
       # ... existing workflows
       'my-workflow': MyWorkflow,
   }

3. **If part of a subcampaign, update ``subcampaign_map``:**

.. code-block:: python

   subcampaign_map = {
       # ... existing mappings
       'my-subcampaign': ['my-workflow', ...],
   }

4. **Write tests:**

.. code-block:: python

   # tests/workflows/test_my_workflow.py
   def test_my_workflow_creation():
       workflow = MyWorkflow(
           name="test",
           executable="my-exe",
           context="test.yaml",
           special_param="value",
           id=1,
       )
       assert workflow.special_param == "value"
       assert workflow.get_arguments() == ["--special=value"]

Enactor Backends
~~~~~~~~~~~~~~~~

To add a new execution backend:

1. **Inherit from base enactor:**

.. code-block:: python

   from socm.enactor.base import Enactor

   class MyEnactor(Enactor):
       def setup(self, resource, walltime, cores, execution_schema=None):
           # Set up the execution backend
           pass

       def enact(self, workflows):
           # Submit workflows for execution
           pass

       def terminate(self):
           # Clean up resources
           pass

       def teardown(self):
           # Cancel the current allocation
           pass

2. **Implement all required methods from** :class:`~socm.enactor.base.Enactor`
3. **Register in bookkeeper:** add a condition in ``Bookkeeper.__init__`` based on a flag

Documentation
-------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make html

The built documentation will be in ``docs/_build/html/``.

Writing Documentation
~~~~~~~~~~~~~~~~~~~~~

1. **Use reStructuredText format** for ``.rst`` files
2. **Use NumPy-style docstrings** for Python source files
3. **Include code examples**
4. **Document all public APIs**
5. **Keep examples up to date**

API Documentation
~~~~~~~~~~~~~~~~~

Use NumPy-style docstrings for all public classes, methods, and functions:

.. code-block:: python

   def my_function(param1: str, param2: int = 0) -> bool:
       """
       Brief description of the function.

       Longer description if needed.

       Parameters
       ----------
       param1 : str
           Description of param1.
       param2 : int, optional
           Description of param2. Defaults to 0.

       Returns
       -------
       bool
           Description of return value.

       Raises
       ------
       ValueError
           If param1 is empty.

       Examples
       --------
       >>> my_function("test", 5)
       True
       """

Release Process
---------------

Version Management
~~~~~~~~~~~~~~~~~~

We use semantic versioning (MAJOR.MINOR.PATCH):

* **MAJOR**: Incompatible API changes
* **MINOR**: New functionality (backward compatible)
* **PATCH**: Bug fixes (backward compatible)

Creating Releases
~~~~~~~~~~~~~~~~~

Releases are managed via GitHub. To create a new release:

1. **Go to the repository on GitHub** and navigate to *Releases*
2. **Draft a new release**, setting the tag value (e.g. ``v1.2.3``) and providing release notes
3. **Publish the release** — this triggers the CI pipeline which builds the package and publishes it to PyPI automatically

Contributing Guidelines
-----------------------

Pull Request Process
~~~~~~~~~~~~~~~~~~~~

1. **Fork** the repository
2. **Create feature branch** from main
3. **Make changes** with appropriate tests
4. **Ensure tests pass** and code style is correct
5. **Submit pull request** with clear description

Code Review
~~~~~~~~~~~

All code changes require review:

* **Functionality**: Does the code work as intended?
* **Tests**: Are there appropriate tests?
* **Style**: Does it follow project conventions?
* **Documentation**: Are changes documented?

Issue Reporting
~~~~~~~~~~~~~~~

When reporting issues:

1. **Use issue templates** when available
2. **Provide minimal reproducible example**
3. **Include environment information**
4. **Check for existing issues** first

Getting Help
------------

* **Documentation**: Start with this documentation
* **Examples**: Check the ``examples/`` directory
* **Issues**: Search existing GitHub issues
* **Discussions**: Use GitHub discussions for questions
* **Code Review**: Learn from pull request reviews
