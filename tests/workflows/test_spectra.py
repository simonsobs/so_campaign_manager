from socm.workflows.spectra import SpectraWorkflow


def test_spectra_workflow_defaults(minimal_config):
    workflow = SpectraWorkflow(**minimal_config)
    assert workflow.name == "pspipe_workflow"
    assert workflow.executable == "python -u"
    assert workflow.subcommand == "script.py"
    assert workflow.resources.ranks == 4
    assert workflow.resources.threads == 2
    assert workflow.datasize == 0
    assert workflow.script_args is None
    assert workflow.script_flags is None
    assert workflow.id is None
    assert workflow.depends == []


def test_spectra_workflow_with_all_fields(full_config):
    workflow = SpectraWorkflow(**full_config)
    assert workflow.script_args == ["file:///some/path/input.fits"]
    assert workflow.script_flags == ["verbose", "debug"]
    assert workflow.config == "config.yaml"
    assert workflow.output == "output_dir"


def test_get_arguments_empty(minimal_config):
    workflow = SpectraWorkflow(**minimal_config)
    assert workflow.get_arguments() == []


def test_get_arguments_file_script_args(minimal_config, tmp_path):
    p = tmp_path / "input.fits"
    p.write_text("")
    minimal_config["script_args"] = [f"file://{p}"]
    workflow = SpectraWorkflow(**minimal_config)
    arguments = workflow.get_arguments()
    assert str(p.absolute()) in arguments


def test_get_arguments_plain_script_args_not_appended(minimal_config):
    """Plain (non-file://) script_args are not appended to arguments."""
    minimal_config["script_args"] = ["plain_arg"]
    workflow = SpectraWorkflow(**minimal_config)
    arguments = workflow.get_arguments()
    assert "plain_arg" not in arguments


def test_get_arguments_script_flags(minimal_config):
    minimal_config["script_flags"] = ["verbose", "no-cache"]
    workflow = SpectraWorkflow(**minimal_config)
    arguments = workflow.get_arguments()
    assert "--verbose" in arguments
    assert "--no-cache" in arguments


def test_get_arguments_kwargs(minimal_config):
    minimal_config["config"] = "config.yaml"
    minimal_config["output"] = "output_dir"
    workflow = SpectraWorkflow(**minimal_config)
    arguments = workflow.get_arguments()
    assert "--config=config.yaml" in arguments
    assert "--output=output_dir" in arguments


def test_get_arguments_excludes_reserved_fields():
    workflow = SpectraWorkflow(
        name="my_workflow",
        executable="python -u",
        subcommand="script.py",
        depends=["other"],
        script_args=["file:///tmp/x.fits"],
        script_flags=["verbose"],
        datasize=100,
        output_dir="out",
        resources={"ranks": 1, "threads": 1},
        config="config.yaml",
    )
    arguments = workflow.get_arguments()
    reserved = ["name", "executable", "subcommand", "depends", "script_args",
                "script_flags", "datasize", "output_dir", "resources", "id",
                "environment", "area"]
    for field in reserved:
        assert not any(arg.startswith(f"--{field}=") for arg in arguments), (
            f"Reserved field '{field}' should not appear in arguments"
        )
    assert "--config=config.yaml" in arguments


def test_get_arguments_order_is_sorted(minimal_config):
    """kwargs are emitted in sorted key order."""
    minimal_config["zzz"] = "last"
    minimal_config["aaa"] = "first"
    workflow = SpectraWorkflow(**minimal_config)
    arguments = workflow.get_arguments()
    kwarg_args = [a for a in arguments if a.startswith("--")]
    keys = [a.split("=")[0][2:] for a in kwarg_args]
    assert keys == sorted(keys)


def test_get_command(minimal_config):
    workflow = SpectraWorkflow(**minimal_config)
    command = workflow.get_command()
    assert command == "srun --cpu_bind=cores --export=ALL --ntasks-per-node=4 --cpus-per-task=2 python -u script.py"


def test_get_command_includes_arguments(minimal_config):
    minimal_config["script_flags"] = ["verbose"]
    minimal_config["config"] = "config.yaml"
    workflow = SpectraWorkflow(**minimal_config)
    command = workflow.get_command()
    assert "--verbose" in command
    assert "--config=config.yaml" in command
    assert command.startswith("srun --cpu_bind=cores --export=ALL --ntasks-per-node=4 --cpus-per-task=2 python -u script.py")


def test_get_workflows_from_dict(minimal_config):
    workflows = SpectraWorkflow.get_workflows(minimal_config)
    assert len(workflows) == 1
    assert isinstance(workflows[0], SpectraWorkflow)
    assert workflows[0].subcommand == "script.py"


def test_get_workflows_from_list(minimal_config):
    configs = [
        {**minimal_config, "id": 1},
        {**minimal_config, "id": 2, "subcommand": "other_script.py"},
    ]
    workflows = SpectraWorkflow.get_workflows(configs)
    assert len(workflows) == 2
    assert workflows[0].id == 1
    assert workflows[1].subcommand == "other_script.py"


def test_get_workflows_preserves_kwargs():
    config = {
        "subcommand": "script.py",
        "resources": {"ranks": 2, "threads": 4},
        "config": "my_config.yaml",
        "output": "results/",
    }
    workflows = SpectraWorkflow.get_workflows(config)
    assert workflows[0].config == "my_config.yaml"
    assert workflows[0].output == "results/"
