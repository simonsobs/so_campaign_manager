# Contributing to SO Campaign Manager

Thank you for your interest in contributing to SO Campaign Manager! This document provides guidelines for contributing to the project.

## Quick Start

For detailed contributing guidelines, please see our **[Developer Guide](docs/developer_guide.rst)**.

## Development Setup

1. **Fork and clone** the repository
2. **Set up development environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -e ".[dev]"
   ```
3. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Standards

- **PEP8 compliance is mandatory** - use `flake8` to check
- **Optional formatting** with `darker` for progressive formatting
- **Write tests** for new functionality
- **Document your code** with Google-style docstrings

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Ensure tests pass and code style is correct
4. Submit a pull request with a clear description

## Documentation

- All public APIs should be documented
- Update relevant documentation for changes
- Build docs locally: `cd docs && make html`

## Getting Help

- 📚 **[Full Documentation](docs/index.rst)** - Complete guides and API reference
- 🐛 **[GitHub Issues](https://github.com/simonsobs/so_campaign_manager/issues)** - Bug reports and feature requests
- 💬 **[GitHub Discussions](https://github.com/simonsobs/so_campaign_manager/discussions)** - Questions and general discussion

## Types of Contributions

We welcome:
- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🧪 Test improvements
- 🔧 Performance optimizations

For detailed information about development workflow, code style, testing, and more, please refer to our **[Developer Guide](docs/developer_guide.rst)**.