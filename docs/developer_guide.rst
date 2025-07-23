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

2. **Create a virtual environment:**

.. code-block:: bash

   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate

3. **Install in development mode:**

.. code-block:: bash

   pip install -e ".[dev]"

4. **Install pre-commit hooks (optional but recommended):**

.. code-block:: bash

   pip install pre-commit
   pre-commit install

Code Style and Quality
----------------------

The project follows strict code quality standards:

PEP8 Compliance (Mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All code must be PEP8 compliant. Use flake8 to check:

.. code-block:: bash

   flake8 src/socm tests/

Code Formatting (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use ``darker`` for progressive code formatting:

.. code-block:: bash

   # Check what would be changed
   darker --diff -r origin/main src/socm -L flake8

   # Apply formatting
   darker -r origin/main src/socm -L flake8

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
   │   │   ├── __init__.py
   │   │   ├── ml_mapmaking.py
   │   │   ├── sat_simulation.py
   │   │   └── ml_null_tests/
   │   ├── enactor/           # Execution backends
   │   │   ├── __init__.py
   │   │   ├── base.py
   │   │   └── rp_enactor.py
   │   ├── planner/           # Campaign planning
   │   │   └── __init__.py
   │   ├── utils/             # Utilities
   │   │   ├── __init__.py
   │   │   ├── const.py
   │   │   ├── misc.py
   │   │   └── states.py
   │   └── configs/           # Default configurations
   ├── tests/                 # Test suite
   ├── examples/              # Example configurations
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
* ``hotfix/abc_123``: Critical fixes for immediate release
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
   pytest tests/
   # Check code style
   flake8 src/socm

3. **Create pull request:**
   * Target ``main`` branch
   * Include description of changes
   * Reference related issues

4. **Code review and merge**

Branch Policies
~~~~~~~~~~~~~~~

* All branches are short-lived
* Limited number of open branches per developer
* Only ``N`` fix branches and ``M << N`` feature branches

Testing
-------

Test Structure
~~~~~~~~~~~~~~

Tests are organized to mirror the package structure:

.. code-block::

   tests/
   ├── __init__.py
   ├── conftest.py            # Test configuration
   ├── test_bookkeeper.py     # Bookkeeper tests
   ├── test_misc.py          # Utility tests
   ├── test_planner.py       # Planner tests
   └── workflows/            # Workflow tests

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=socm

   # Run specific test file
   pytest tests/test_bookkeeper.py

   # Run with verbose output
   pytest -v

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
       return Campaign(id=1, workflows=[], campaign_policy="time")

Adding New Features
-------------------

Workflow Types
~~~~~~~~~~~~~~

To add a new workflow type:

1. **Create workflow class:**

.. code-block:: python

   # src/socm/workflows/my_workflow.py
   from socm.core.models import Workflow

   class MyWorkflow(Workflow):
       special_param: str
       
       def get_command(self, **kwargs) -> str:
           return f"{self.executable} {self.subcommand}"
       
       def get_arguments(self, **kwargs) -> str:
           return f"--special {self.special_param}"

2. **Register workflow:**

.. code-block:: python

   # src/socm/workflows/__init__.py
   from .my_workflow import MyWorkflow

   registered_workflows = {
       # ... existing workflows
       'my-workflow': MyWorkflow,
   }

3. **Add to subcampaign mapping:**

.. code-block:: python

   subcampaign_map = {
       # ... existing mappings
       'my-workflow': 'my-workflow',
   }

4. **Write tests:**

.. code-block:: python

   # tests/workflows/test_my_workflow.py
   def test_my_workflow_creation():
       workflow = MyWorkflow(
           name="test",
           executable="my-exe",
           context="test.yaml",
           special_param="value"
       )
       assert workflow.special_param == "value"

Enactor Backends
~~~~~~~~~~~~~~~~

To add a new execution backend:

1. **Inherit from base enactor:**

.. code-block:: python

   from socm.enactor.base import BaseEnactor

   class MyEnactor(BaseEnactor):
       def submit_jobs(self, jobs):
           # Implementation
           pass

2. **Implement required methods**
3. **Register in bookkeeper**

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

1. **Use reStructuredText format**
2. **Include code examples**
3. **Document all public APIs**
4. **Keep examples up to date**

API Documentation
~~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def my_function(param1: str, param2: int = 0) -> bool:
       """Brief description of the function.

       Longer description if needed.

       Args:
           param1: Description of param1.
           param2: Description of param2. Defaults to 0.

       Returns:
           Description of return value.

       Raises:
           ValueError: If param1 is empty.

       Example:
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

1. **Update version** in ``pyproject.toml``
2. **Update CHANGELOG** with release notes
3. **Create release branch:**

.. code-block:: bash

   git checkout -b release/v1.2.3

4. **Create tag and release** via GitHub

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