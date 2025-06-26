import radical.utils as ru

from socm.core import Resource, Workflow
from socm.planner import HeftPlanner

try:
    import mock
except ImportError:
    from unittest import mock


# ------------------------------------------------------------------------------
#
@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_plan(mocked_init):
    # Create Workflow objects for the campaign
    workflows = [
        Workflow(name=f"W{i+1}", executable="exe", context="ctx", subcommand="sub", id=i+1)
        for i in range(10)
    ]
    # Map workflow names to objects for easy lookup
    {wf.name: wf for wf in workflows}

    actual_plan = [(Workflow(name='W1', executable='exe', context='ctx', subcommand='sub', id=1, environment=None, resources=None), range(64, 128), 2000, 0, 45), 
                   (Workflow(name='W2', executable='exe', context='ctx', subcommand='sub', id=2, environment=None, resources=None), range(128, 144), 15000, 0, 25), 
                   (Workflow(name='W3', executable='exe', context='ctx', subcommand='sub', id=3, environment=None, resources=None), range(0, 1), 2000, 0, 560), 
                   (Workflow(name='W4', executable='exe', context='ctx', subcommand='sub', id=4, environment=None, resources=None), range(16, 24), 32000, 0, 140), 
                   (Workflow(name='W5', executable='exe', context='ctx', subcommand='sub', id=5, environment=None, resources=None), range(8, 16), 1000, 0, 145), 
                   (Workflow(name='W6', executable='exe', context='ctx', subcommand='sub', id=6, environment=None, resources=None), range(0, 112), 20000, 560, 570), 
                   (Workflow(name='W7', executable='exe', context='ctx', subcommand='sub', id=7, environment=None, resources=None), range(56, 112), 6000, 45, 65), 
                   (Workflow(name='W8', executable='exe', context='ctx', subcommand='sub', id=8, environment=None, resources=None), range(32, 64), 1000, 0, 30
                   )]
    planner = HeftPlanner(None, None, None)
    planner._logger = ru.Logger("dummy")
    planner._est_memory = list()

    planner._resource_requirements = {
        "W1": {"req_walltime": 45, "req_cpus": 64, "req_memory": 2000},
        "W2": {"req_walltime": 25, "req_cpus": 16, "req_memory": 15000},
        "W3": {"req_walltime": 560, "req_cpus": 1, "req_memory": 2000},
        "W4": {"req_walltime": 140, "req_cpus": 8, "req_memory": 32000},
        "W5": {"req_walltime": 145, "req_cpus": 8, "req_memory": 1000},
        "W6": {"req_walltime": 10, "req_cpus": 112, "req_memory": 20000},
        "W7": {"req_walltime": 20, "req_cpus": 56, "req_memory": 6000},
        "W8": {"req_walltime": 30, "req_cpus": 32, "req_memory": 1000},
    }

    planner._campaign = workflows
    planner._resources = Resource(
        name="tiger3",
        nodes=2,
        cores_per_node=112,
        memory_per_node=64 * 1024,  # in MB
        default_queue="normal",
        maximum_walltime=1440,  # in minutes
    )
    planner._num_oper = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    est_plan, _ = planner.plan()

    assert est_plan == actual_plan
