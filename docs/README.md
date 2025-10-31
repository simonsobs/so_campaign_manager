# SO Campaign Manager Documentation

This directory contains the comprehensive Sphinx documentation for SO Campaign Manager.

## Building the Documentation

To build the HTML documentation:

```bash
cd docs
make html
```

The built documentation will be available in `_build/html/index.html`.

To view the documentation:

```bash
# On macOS
open _build/html/index.html

# On Linux
xdg-open _build/html/index.html

# Or use a local web server
python -m http.server 8000 --directory _build/html
# Then visit http://localhost:8000
```

## Requirements

The documentation build requires:

- sphinx
- sphinx-rtd-theme
- sphinxcontrib-napoleon
- sphinx-autodoc-typehints
- myst-parser (optional, for markdown support)

Install all documentation dependencies with:

```bash
pip install -e ".[docs]"
```

Or install manually:

```bash
pip install sphinx sphinx-rtd-theme sphinxcontrib-napoleon sphinx-autodoc-typehints
```

## Documentation Structure

### Getting Started
- `installation.rst` - Installation instructions and requirements
- `quickstart.rst` - Quick start guide (5-minute introduction)
- `tutorial.rst` - **NEW** Comprehensive step-by-step tutorials

### User Documentation
- `user_guide.rst` - Comprehensive reference for all features
- `workflows.rst` - Available workflows and configuration
- `faq.rst` - **NEW** Frequently asked questions and troubleshooting

### Advanced Topics
- `architecture.rst` - **NEW** System architecture and design patterns
- `advanced_topics.rst` - **NEW** Custom workflows, planners, and advanced features

### API Reference
- `api.rst` - Public API reference
- `api_complete.rst` - Complete API reference (including private members)

### Development
- `developer_guide.rst` - Contributing and development setup

## Documentation Features

### Comprehensive Coverage

This documentation includes:

1. **Getting Started Guides**: Installation, quick start, and tutorials for new users
2. **User Documentation**: Complete reference for configuration, workflows, and common tasks
3. **Architecture Documentation**: Deep dive into system design and components
4. **Advanced Topics**: Custom development, extensions, and power-user features
5. **API Reference**: Both public and complete API documentation
6. **Troubleshooting**: FAQ and debugging guides

### Enhanced Features

- **Read the Docs Theme**: Professional, responsive theme with search
- **Custom Footer**: Credits Claude Code for documentation assistance
- **Hierarchical Organization**: Logical grouping by user type and topic
- **Cross-references**: Extensive linking between related topics
- **Code Examples**: Abundant examples in TOML and Python
- **Visual Diagrams**: Architecture diagrams and flowcharts
- **Search Functionality**: Full-text search across all documentation

### Tutorial Topics

The tutorial section covers:

1. Your First Campaign - Basic single-workflow campaign
2. Multiple Workflows in Parallel - Running multiple workflows
3. Null Test Campaigns - Comprehensive null test suites
4. Resource Optimization - Right-sizing and performance tuning
5. Advanced Configuration Patterns - Environment variables, multi-stage processing
6. Monitoring and Debugging - Troubleshooting and log analysis
7. Testing Before Production - Dry-run mode and validation
8. Programmatic Usage - Using the Python API

### Advanced Topics

The advanced topics section covers:

1. Custom Workflow Development - Creating new workflow types
2. Custom Planner Development - Implementing scheduling algorithms
3. Custom Enactor Development - Alternative execution backends
4. Resource Prediction - Slurmise integration
5. Multi-Campaign Orchestration - Dependent campaigns
6. Performance Optimization - Profiling and tuning
7. Integration with Other Tools - Nextflow, Snakemake, etc.
8. Custom Callbacks and Hooks - Event-driven customization

## Building for Read the Docs

This documentation is configured for Read the Docs deployment. The configuration includes:

- Automatic API documentation generation
- Module mocking for unavailable dependencies
- Intersphinx linking to Python, NumPy, and Pydantic docs
- GitHub integration for "Edit on GitHub" links
- Version display in sidebar

## Contributing to Documentation

When updating documentation:

1. Follow reStructuredText formatting guidelines
2. Include code examples for new features
3. Add cross-references to related sections
4. Update the index.rst table of contents if adding new files
5. Test the build locally before committing
6. Ensure all links work and there are no Sphinx warnings

### Writing Style

- Use clear, concise language
- Include practical examples
- Explain both "how" and "why"
- Link to related documentation
- Use admonitions (note, warning, tip) appropriately

## Cleaning Build Artifacts

To clean build artifacts:

```bash
cd docs
make clean
```

## Maintenance

This documentation was created with assistance from Claude Code, an AI coding assistant by Anthropic. For questions or improvements, please:

1. Check the FAQ section first
2. Search existing GitHub issues
3. Open a new issue with the documentation label
4. Submit a pull request with improvements

## License

The documentation is part of the SO Campaign Manager project and follows the same license terms.