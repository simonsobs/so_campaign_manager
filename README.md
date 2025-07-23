[![PyPI - Version](https://img.shields.io/pypi/v/so_campaign_manager.svg)](https://pypi.org/project/so_campaign_manager)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/so_campaign_manager.svg)](https://pypi.org/project/so_campaign_manager)
![CI workflow](https://github.com/simonsobs/so_campaign_manager/actions/workflows/test.yaml/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/simonsobs/so_campaign_manager/badge.svg?branch=main)](https://coveralls.io/github/simonsobs/so_campaign_manager?branch=main)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15784156.svg)](https://doi.org/10.5281/zenodo.15784156)
[![Docs Status](https://readthedocs.org/projects/so-campaign-manager/badge/?version=latest&style=flat)](https://so-campaign-manager.readthedocs.io)


## SO Campaign Manager

This repository holds the code of the software tools that will run the mapmaking campaign on Tiger 3.

The project has three big aspects:
1. Providing a method to submit new workflows, update existing ones and delete via configuration or a series of commands
2. Based on the workflow configuration set the resource requirement accordingly and submit it to SLURM. Resource configuration can be based on:
    1. Total size of observations and their file distribution
    2. A specific observation mapping between processes and files
    3. Node memory and node processor performance.
3. Use a workflow management tool to execute all workflows in the minimum amount of time.

## Documentation

📚 **[Full Documentation](docs/index.rst)** - Complete documentation including:

- [Installation Guide](docs/installation.rst) - Setup and installation instructions
- [Quick Start](docs/quickstart.rst) - Get started quickly with examples
- [User Guide](docs/user_guide.rst) - Comprehensive usage guide
- [API Reference](docs/api.rst) - Complete API documentation
- [Workflow Guide](docs/workflows.rst) - Available workflows and how to use them
- [Developer Guide](docs/developer_guide.rst) - Contributing and development setup

### Building Documentation

To build the HTML documentation locally:

```bash
cd docs
pip install sphinx sphinx-rtd-theme
make html
```

The documentation will be available in `docs/_build/html/index.html`.

## Quick Start

Install the package:

```bash
pip install so_campaign_manager
```

Create a configuration file (`campaign.toml`):

```toml
[campaign]
deadline = "2d"

[campaign.resources]
nodes = 4
cores-per-node = 112

[campaign.ml-mapmaking]
context = "file:///path/to/context.yaml"
output_dir = "/path/to/output"
bands = "f090"
# ... other parameters
```

Run your campaign:

```bash
socm -t campaign.toml
```

For detailed examples and configuration options, see the [documentation](docs/).

---

## Development guide

### Branching model

* the latest development is in the `main` branch.
* bug fixes:
  * branch of `main`, naming convention: `fix/issue_1234` (reference github issue). `hotfix/issue_1234` if it is a major issue that needs resolution as soon as possible.
  * fix in that branch, and test
  * create pull request toward `main`
  * code review, then merge  
* major development activities go into feature branches 
  * branch `main` into `feature/feature_name`
  * work on that feature branch
  * on completion, merge `main` into the feature branch.
  * test the feature branch
  * create a pull request for merging the feature branch into `main` (that should be a fast-forward now)
  * merging of feature branches into `main` should be only after code review 
* documentation changes are handled like fix or feature branches, depending on size and impact, similar to code changes

#### Branch Naming

 * `main`: *never* commit directly
 * `feature/abc`: development of new features
 * `fix/abc_123`: referring to ticket 123
 * `hotfix/abc_123`: referring to ticket 123, to be released right after merge to master
 * `tmp/abc`: temporary branch, will be deleted soon
 * `test/abc`: test some integration, like a merge of two feature branches

For the latter: assume you want to test how `feature/a` works in combination with `feature/b`, then:
 * `git checkout feature/a`
 * `git checkout -b test/a_b`
 * `git merge feature/b`
 * do tests  

#### Branching Policies

All branches are short living. To support this, only a limited number of branches should be open at any point in time. Only `N` branches for fixes and `M << N` branches for features should be open for each developer - other features / issues have to wait.
 

### Ensure PEP8 compliance (mandatory) and format your code with Darker (optional)

`darker` is a *partial formatting* tool that helps to reformat new or modified code lines so the codebase progressively adapts a code style instead of doing a full reformat, which would be a big commitment. It was designed with the ``black`` formatter in mind, hence the name.

In this repo **we only require PEP8 compliance**, so if you want to make sure that your PR passes the darker bot, you'll need both darker and `flake8`:

    pip install darker flake8


You'll also need the original codebase so darker can first get a diff between the current ``develop`` branch and your code.
After making your changes to your local branch, check your modifications on the package:

    darker --diff -r origin/develop package/src -L flake8

Darker will first suggest changes so that the new code lines comply with ``black``'s rules, and then show flake8 errors and warnings.

You are free to skip the diffs and then manually fix the PEP8 faults.
Or if you're ok with the suggested formatting changes, just apply the suggested fixes: ::

    darker -r origin/develop package/scr -L flake8

