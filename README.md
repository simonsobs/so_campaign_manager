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

It is necessary that the project maintains good code style and has a low threshold for other people to contribute. For that reason, Black code formatting, linting, and typing are essential. They may increase the time to development slightly, but they significantly reduce the time to contribution.

Unit tests are also required for every function that does something significant.

When contributing code please use darker.