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

2. **Install the package with the development tools:**

.. code-block:: bash

   uv sync --all-extras --group dev

3. **Install the pre-commit hooks** (ruff, isort, whitespace checks, and a
   conventional-commit check on commit messages):

.. code-block:: bash

   uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

Code Style and Quality
----------------------

The project follows strict code quality standards:

PEP8 Compliance (Mandatory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All code must be PEP8 compliant with a maximum line length of 120 characters
(configured in ``pyproject.toml``). CI runs ruff and isort on every pull request:

.. code-block:: bash

   uv run ruff check src tests
   uv run isort --check-only src tests

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
   ├── src/socm/
   │   ├── __main__.py        # CLI entry point: socm <subcommand>
   │   ├── execs/             # one module per subcommand: mapmaking, power_spectra, lat_sims
   │   ├── core/models.py     # Pydantic models: Workflow, Campaign, DAG, Resource, ...
   │   ├── bookkeeper/        # orchestration: planning, enacting, monitoring
   │   ├── planner/           # Planner base class and the HEFT planner
   │   ├── enactor/           # Enactor base class, RADICAL-Pilot and dry-run enactors
   │   ├── resources/         # tiger, perlmutter, universe, localhost
   │   ├── workflows/         # workflow classes; __init__.py has registered_workflows
   │   │   └── ml_null_tests/ # one module per null test
   │   └── utils/             # misc (config and par-file parsing), log, states
   ├── tests/                 # test suite; tests/workflows/ for workflow classes
   ├── examples/              # example campaign configurations
   ├── docs/
   └── pyproject.toml

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
   uv run pytest tests/
   uv run ruff check src tests
   uv run isort --check-only src tests

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

Tests mirror the package: ``tests/test_<module>.py`` for each component and
``tests/workflows/`` for the workflow classes. ``tests/conftest.py`` replaces
``radical.*`` and ``slurmise`` with mocks, so the suite runs without an HPC
allocation and on macOS. Tests must not read files from ``examples/``, which users
change freely; create what a test needs in ``tmp_path``.

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

:doc:`advanced_topics` shows how to add a workflow type, a planner or an enactor, and
:doc:`resources` how to add a cluster.

Documentation
-------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   uv sync --all-extras --group docs
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
