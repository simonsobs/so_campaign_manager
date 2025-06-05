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

## Development guide

### Branching model
We use **[git-flow](http://nvie.com/posts/a-successful-git-branching-model/)** as branching model, with some simplifications.  We follow **[semantic version numbering](http://semver.org/)**.

* release candidates and releases are tagged in the `main` branch.
* urgent hotfix releases:
  * branch from master to `hotfix/problem_name`
  * fix the problem in that branch
  * test that branch
  * merge back to main and prepare a release
* normal bug fixes:
  * branch of `develop`, naming convention: `fix/issue_1234` (reference github issue)
  * fix in that branch, and test
  * create pull request toward devel
  * code review, then merge  
* major development activities go into feature branches 
  * branch `develop` into `feature/feature_name`
  * work on that feature branch
  * on completion, merge `develop` into the feature branch.
  * test the feature branch
  * create a pull request for merging the feature branch into `develop` (that should be a fast-forward now)
  * merging of feature branches into `develop` should be discussed with the group *before* they are performed, and only after code review 
* documentation changes are handled like fix or feature branches, depending on size and impact, similar to code changes

#### Branch Naming

 * `develop`, `main`: *never* commit directly to those
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

