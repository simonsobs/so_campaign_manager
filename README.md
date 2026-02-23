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

For information on contributing, branching model, and code style requirements, see [CONTRIBUTING.md](CONTRIBUTING.md).
