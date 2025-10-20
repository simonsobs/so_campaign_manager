import humanfriendly
import numpy as np
import pytest
import radical.utils as ru

from socm.core import QosPolicy, Resource, Workflow
from socm.planner import HeftPlanner, PlanEntry
from socm.resources import TigerResource

try:
    import mock
except ImportError:
    from unittest import mock

def compare_entries(expected_entry: PlanEntry, test_entry: PlanEntry) -> bool:
    assert expected_entry.workflow == test_entry.workflow
    assert expected_entry.cores == test_entry.cores
    assert expected_entry.memory == test_entry.memory
    assert np.isclose(expected_entry.start_time, test_entry.start_time)
    assert np.isclose(expected_entry.end_time, test_entry.end_time)

# ------------------------------------------------------------------------------
#
@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_plan(mocked_init):
    # Create Workflow objects for the campaign
    workflows = [
        Workflow(
            name=f"W{i+1}", executable="exe", context="ctx", subcommand="sub", id=i + 1
        )
        for i in range(10)
    ]
    # Map workflow names to objects for easy lookup
    {wf.name: wf for wf in workflows}

    actual_plan = [
        PlanEntry(workflow=Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1, environment=None, resources=None), cores=range(64, 128), memory=2000, start_time=0, end_time=45),
        PlanEntry(workflow=Workflow(name="W2", executable="exe", context="ctx", subcommand="sub", id=2, environment=None, resources=None), cores=range(128, 144), memory=15000, start_time=0, end_time=25),
        PlanEntry(workflow=Workflow(name="W3", executable="exe", context="ctx", subcommand="sub", id=3, environment=None, resources=None), cores=range(0, 1), memory=2000, start_time=0, end_time=560),
        PlanEntry(workflow=Workflow(name="W4", executable="exe", context="ctx", subcommand="sub", id=4, environment=None, resources=None), cores=range(16, 24), memory=32000, start_time=0, end_time=140),
        PlanEntry(workflow=Workflow(name="W5", executable="exe", context="ctx", subcommand="sub", id=5, environment=None, resources=None), cores=range(8, 16), memory=1000, start_time=0, end_time=145),
        PlanEntry(workflow=Workflow(name="W6", executable="exe", context="ctx", subcommand="sub", id=6, environment=None, resources=None), cores=range(112, 224), memory=20000, start_time=45, end_time=55),
        PlanEntry(workflow=Workflow(name="W7", executable="exe", context="ctx", subcommand="sub", id=7, environment=None, resources=None), cores=range(168, 224), memory=6000, start_time=0, end_time=20),
        PlanEntry(workflow=Workflow(name="W8", executable="exe", context="ctx", subcommand="sub", id=8, environment=None, resources=None), cores=range(32, 64), memory=1000, start_time=0, end_time=30),
    ]
    planner = HeftPlanner(None, None, None)
    planner._logger = ru.Logger("dummy")
    planner._est_memory = list()

    planner._resource_requirements = {
        "W1": {"req_cpus": 64, "req_memory": 2000, "req_walltime": 45},
        "W2": {"req_cpus": 16, "req_memory": 15000, "req_walltime": 25},
        "W3": {"req_cpus": 1, "req_memory": 2000, "req_walltime": 560},
        "W4": {"req_cpus": 8, "req_memory": 32000, "req_walltime": 140},
        "W5": {"req_cpus": 8, "req_memory": 1000, "req_walltime": 145},
        "W6": {"req_cpus": 112, "req_memory": 20000, "req_walltime": 10},
        "W7": {"req_cpus": 56, "req_memory": 6000, "req_walltime": 20},
        "W8": {"req_cpus": 32, "req_memory": 1000, "req_walltime": 30},
    }

    planner._campaign = workflows
    planner._resources = Resource(
        name="tiger3",
        nodes=2,
        cores_per_node=112,
        memory_per_node=64 * 1024,  # in MB
    )
    planner._num_oper = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    est_plan, _ = planner._calculate_plan()

    assert est_plan == actual_plan


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_failing_plan(mocked_init):
    workflows = [
        Workflow(name="ml_mapmaking_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=1, environment={}, resources={"ranks": 896, "threads": 8, "memory": 64000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/output", query="file://obslist_balanced.txt", datasize=5230991388, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, wafer="ws0"),
        Workflow(name="mission_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=2, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/mission_split_1", query="file://query.txt", datasize=1311130012, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="mission_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=3, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/mission_split_2", query="file://query.txt", datasize=1307133118, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="mission_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=4, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/mission_split_3", query="file://query.txt", datasize=1305106812, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="mission_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=5, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/mission_split_4", query="file://query.txt", datasize=1307621446, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="wafer_ws0_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=6, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/wafer_ws0_split_1", query="file://query.txt", datasize=1311130012, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="wafer_ws0_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=7, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/wafer_ws0_split_2", query="file://query.txt", datasize=1307133118, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="wafer_ws0_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=8, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/wafer_ws0_split_3", query="file://query.txt", datasize=1305106812, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="wafer_ws0_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=9, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/wafer_ws0_split_4", query="file://query.txt", datasize=1307621446, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_rising_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=10, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_rising_split_1", query="file://query.txt", datasize=691266434, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_rising_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=11, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_rising_split_2", query="file://query.txt", datasize=689067348, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_rising_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=12, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_rising_split_3", query="file://query.txt", datasize=689196634, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_rising_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=13, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_rising_split_4", query="file://query.txt", datasize=689290508, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_setting_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=14, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_setting_split_1", query="file://query.txt", datasize=615677782, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_setting_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=15, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_setting_split_2", query="file://query.txt", datasize=621404494, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_setting_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=16, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_setting_split_3", query="file://query.txt", datasize=618468316, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
        Workflow(name="direction_setting_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=17, environment={}, resources={"ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000}, area="file:///geometry.fits", output_dir="/direction_setting_split_4", query="file://query.txt", datasize=616619872, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0"),
    ]

    actual_plan = [
        PlanEntry(workflow=Workflow( name="ml_mapmaking_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=1, environment={}, resources={"ranks": 896,"threads": 8,"memory": 64000000,"runtime": 12000,}, area="file:///geometry.fits", output_dir="/output", query="file://obslist_balanced.txt", datasize=5230991388, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, wafer="ws0", ), cores=range(0, 7168), memory=64000000, start_time=0, end_time=13200,),
        PlanEntry(workflow=Workflow( name="mission_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=2, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/mission_split_1", query="file://query.txt", datasize=1311130012, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(0, 1792), memory=16000000, start_time=13200, end_time=26400),
        PlanEntry(workflow=Workflow( name="mission_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=3, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/mission_split_2", query="file://query.txt", datasize=1307133118, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(1792, 3584), memory=16000000, start_time=13200, end_time=26400,),
        PlanEntry(workflow=Workflow( name="mission_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=4, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/mission_split_3", query="file://query.txt", datasize=1305106812, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(3584, 5376), memory=16000000, start_time=13200, end_time=26400,),
        PlanEntry(workflow=Workflow( name="mission_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=5, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/mission_split_4", query="file://query.txt", datasize=1307621446, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(5376, 7168), memory=16000000, start_time=13200, end_time=26400,),
        PlanEntry(workflow=Workflow( name="wafer_ws0_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=6, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/wafer_ws0_split_1", query="file://query.txt", datasize=1311130012, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(0, 1792), memory=16000000, start_time=26400, end_time=39600,),
        PlanEntry(workflow=Workflow( name="wafer_ws0_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=7, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/wafer_ws0_split_2", query="file://query.txt", datasize=1307133118, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(1792, 3584), memory=16000000, start_time=26400, end_time=39600,),
        PlanEntry(workflow=Workflow( name="wafer_ws0_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=8, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/wafer_ws0_split_3", query="file://query.txt", datasize=1305106812, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(3584, 5376), memory=16000000, start_time=26400, end_time=39600,),
        PlanEntry(workflow=Workflow( name="wafer_ws0_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=9, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/wafer_ws0_split_4", query="file://query.txt", datasize=1307621446, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(5376, 7168), memory=16000000, start_time=26400, end_time=39600,),
        PlanEntry(workflow=Workflow( name="direction_rising_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=10, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_rising_split_1", query="file://query.txt", datasize=691266434, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(0, 1792), memory=16000000, start_time=39600, end_time=52800,),
        PlanEntry(workflow=Workflow( name="direction_rising_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=11, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_rising_split_2", query="file://query.txt", datasize=689067348, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(1792, 3584), memory=16000000, start_time=39600, end_time=52800,),
        PlanEntry(workflow=Workflow( name="direction_rising_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=12, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_rising_split_3", query="file://query.txt", datasize=689196634, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(3584, 5376), memory=16000000, start_time=39600, end_time=52800,),
        PlanEntry(workflow=Workflow( name="direction_rising_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=13, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_rising_split_4", query="file://query.txt", datasize=689290508, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(5376, 7168), memory=16000000, start_time=39600, end_time=52800,),
        PlanEntry(workflow=Workflow( name="direction_setting_split_1_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=14, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_setting_split_1", query="file://query.txt", datasize=615677782, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(0, 1792), memory=16000000, start_time=52800, end_time=66000,),
        PlanEntry(workflow=Workflow( name="direction_setting_split_2_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=15, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_setting_split_2", query="file://query.txt", datasize=621404494, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(1792, 3584), memory=16000000, start_time=52800, end_time=66000,),
        PlanEntry(workflow=Workflow( name="direction_setting_split_3_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=16, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000, }, area="file:///geometry.fits", output_dir="/direction_setting_split_3", query="file://query.txt", datasize=618468316, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0", ), cores=range(3584, 5376), memory=16000000, start_time=52800, end_time=66000,),
        PlanEntry(workflow=Workflow(name="direction_setting_split_4_null_test_workflow", executable="so-site-pipeline", context="file:///context.yaml", subcommand="make-ml-map", id=17, environment={}, resources={ "ranks": 224, "threads": 8, "memory": 16000000, "runtime": 12000,}, area="file:///geometry.fits", output_dir="/direction_setting_split_4", query="file://query.txt", datasize=616619872, comps="TQU", wafers=None, bands="f090", nmat="corr", max_dets=None, site="act", downsample=1, maxiter=100, tiled=1, chunk_nobs=1, chunk_duration=None, nsplits=4, wafer="ws0",),cores=range(5376, 7168),memory=16000000,start_time=52800,end_time=66000,),
    ]

    planner = HeftPlanner(None, None, None)
    planner._logger = ru.Logger("dummy")
    planner._est_memory = list()

    planner._resource_requirements = {
        1: {"req_cpus": 7168, "req_memory": 64000000, "req_walltime": 13200.000000000002},
        2: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        3: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        4: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        5: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        6: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        7: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        8: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        9: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        10: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        11: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        12: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        13: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        14: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        15: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        16: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
        17: {"req_cpus": 1792, "req_memory": 16000000, "req_walltime": 13200.000000000002},
    }

    planner._campaign = workflows
    planner._resources = Resource(
        name="tiger3",
        nodes=64,
        cores_per_node=112,
        memory_per_node=humanfriendly.parse_size("1TB") // 1000000,  # in MB
    )
    # breakpoint()
    est_plan, _ = planner._calculate_plan()
    for expected_entry, planned_entry in zip(actual_plan, est_plan):
        compare_entries(expected_entry=expected_entry, test_entry=planned_entry)


# New test cases for helper methods
@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_get_max_ncores(mocked_init):
    """Test that _get_max_ncores returns the maximum CPU requirement."""
    planner = HeftPlanner(None, None, None)

    resource_requirements = {
        1: {"req_cpus": 64, "req_memory": 2000, "req_walltime": 45},
        2: {"req_cpus": 128, "req_memory": 4000, "req_walltime": 60},
        3: {"req_cpus": 32, "req_memory": 1000, "req_walltime": 30},
    }

    max_ncores = planner._get_max_ncores(resource_requirements)
    assert max_ncores == 128


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_initialize_resource_estimates(mocked_init):
    """Test that resource estimates are properly initialized."""
    planner = HeftPlanner(None, None, None)

    resource_requirements = {
        1: {"req_cpus": 64, "req_memory": 2000, "req_walltime": 45},
        2: {"req_cpus": 16, "req_memory": 15000, "req_walltime": 25},
    }

    planner._initialize_resource_estimates(resource_requirements)

    assert planner._est_tx == [45, 25]
    assert planner._est_cpus == [64, 16]
    assert planner._est_memory == [2000, 15000]


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_get_sorted_workflow_indices(mocked_init):
    """Test that workflows are sorted by execution time (longest first)."""
    planner = HeftPlanner(None, None, None)
    planner._est_tx = [45, 25, 560, 140, 145]

    sorted_indices = planner._get_sorted_workflow_indices()

    # Should be sorted in descending order: 560, 145, 140, 45, 25
    assert sorted_indices == [2, 4, 3, 0, 1]


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_initialize_resource_free_times(mocked_init):
    """Test initialization of resource free times."""
    planner = HeftPlanner(None, None, None)
    resources = range(10)

    # Test with float
    result = planner._initialize_resource_free_times(resources, 5.0)
    assert len(result) == 10
    assert all(t == 5.0 for t in result)

    # Test with list
    result = planner._initialize_resource_free_times(resources, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert len(result) == 10
    assert list(result) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # Test with None/other (defaults to 0)
    result = planner._initialize_resource_free_times(resources, None)
    assert len(result) == 10
    assert all(t == 0.0 for t in result)


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_get_free_memory(mocked_init):
    """Test memory availability calculation."""
    planner = HeftPlanner(None, None, None)
    planner._resources = Resource(
        name="test",
        nodes=2,
        cores_per_node=10,
        memory_per_node=1000,  # 2000 total
    )

    # Create a mock plan with PlanEntry
    planner._plan = [
        PlanEntry(workflow=Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1), cores=range(0, 5), memory=500, start_time=0, end_time=100),
        PlanEntry(workflow=Workflow(name="W2", executable="exe", context="ctx", subcommand="sub", id=2), cores=range(5, 10), memory=300, start_time=50, end_time=150),
    ]

    # At time 25: only W1 is running (500 used)
    assert planner._get_free_memory(25, 2) == 1500

    # At time 75: both W1 and W2 are running (800 used)
    assert planner._get_free_memory(75, 2) == 1200

    # At time 125: only W2 is running (300 used)
    assert planner._get_free_memory(125, 2) == 1700

    # At time 200: nothing running
    assert planner._get_free_memory(200, 2) == 2000


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_find_suitable_qos_policies_basic(mocked_init):
    """Test finding suitable QoS policies that meet deadline."""
    planner = HeftPlanner(None, None, None)
    planner._objective = 15

    # Create QoS policies with different max walltimes
    planner._resources = TigerResource(
        name="test",
        nodes=2,
        cores_per_node=10,
        memory_per_node=1000,
    )
    planner._resources.qos=[
            QosPolicy(name="vshort", max_walltime=30, max_jobs=10, max_cores=100),
            QosPolicy(name="short", max_walltime=60, max_jobs=20, max_cores=200),
            QosPolicy(name="medium", max_walltime=120, max_jobs=15, max_cores=300),
            QosPolicy(name="long", max_walltime=240, max_jobs=10, max_cores=400),
        ]

    suitable = planner._find_suitable_qos_policies(cores=10)
    assert suitable == QosPolicy(name="vshort", max_walltime=30, max_jobs=10, max_cores=100)
    suitable = planner._find_suitable_qos_policies(cores=110)
    assert suitable == QosPolicy(name="short", max_walltime=60, max_jobs=20, max_cores=200)
    suitable = planner._find_suitable_qos_policies(cores=210)
    assert suitable == QosPolicy(name="medium", max_walltime=120, max_jobs=15, max_cores=300)
    suitable = planner._find_suitable_qos_policies(cores=310)
    assert suitable == QosPolicy(name="long", max_walltime=240, max_jobs=10, max_cores=400)
    with pytest.raises(ValueError):
        suitable = planner._find_suitable_qos_policies(cores=410)
