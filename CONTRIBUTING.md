# Contributing to SO Campaign Manager

## Development setup

Fork and clone the repository, then install the development dependencies:

```bash
uv sync --group dev
```

## Branching model

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

### Branch naming

 * `main`: *never* commit directly
 * `feature/abc`: development of new features
 * `fix/abc_123`: referring to ticket 123
 * `tmp/abc`: temporary branch, will be deleted soon
 * `test/abc`: test some integration, like a merge of two feature branches

For the latter: assume you want to test how `feature/a` works in combination with `feature/b`, then:
 * `git checkout feature/a`
 * `git checkout -b test/a_b`
 * `git merge feature/b`
 * do tests

### Branching policies

All branches are short living. To support this, only a limited number of branches should be open at any point in time. Only `N` branches for fixes and `M << N` branches for features should be open for each developer - other features / issues have to wait.

## Ensure PEP8 compliance (mandatory) and format your code with Darker (optional)

`darker` is a *partial formatting* tool that helps to reformat new or modified code lines so the codebase progressively adapts a code style instead of doing a full reformat, which would be a big commitment. It was designed with the ``black`` formatter in mind, hence the name.

In this repo **we only require PEP8 compliance**, so if you want to make sure that your PR passes the darker bot, you'll need both darker and `flake8`. These are included in the dev dependencies, so after running `uv sync --group dev` you can check your modifications on the package:

    uv run darker --diff -r origin/main src/ -L flake8

Darker will first suggest changes so that the new code lines comply with ``black``'s rules, and then show flake8 errors and warnings.

You are free to skip the diffs and then manually fix the PEP8 faults.
Or if you're ok with the suggested formatting changes, just apply the suggested fixes:

    uv run darker -r origin/main src/ -L flake8

## Running tests

```bash
uv run pytest -vvv tests/ --cov
```

## Getting help

- 📚 **[Full Documentation](docs/index.rst)**
- 🐛 **[GitHub Issues](https://github.com/simonsobs/so_campaign_manager/issues)** - bug reports and feature requests
- 💬 **[GitHub Discussions](https://github.com/simonsobs/so_campaign_manager/discussions)** - questions and general discussion
