## SO Auto Mapmaker

This repository holds the code of the software tools that will run the mapmaking campaign on Tiger 3.

The project has three big aspects:
1. Providing a method to submit new workflows, update existing ones and delete via configuration or a series of commands
2. Based on the workflow configuration set the resource requirement accordingly and submit it to SLURM. Resource configuration can be based on:
    1. Total size of observations and their file distribution
    2. A specific observation mapping between processes and files
    3. Node memory and node processor performance.
3. Use a workflow management tool to execute all workflows in the minimum amount of time.

Note: This document will fill up as requirements are coming in and we run things. Important aspect is a performance evaluation of the selected workflow.

---

## Development guide:

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

