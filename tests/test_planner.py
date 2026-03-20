from unittest import mock
from unittest.mock import MagicMock

import humanfriendly
import numpy as np
import pytest

from socm.core import DAG, Campaign, QosPolicy, Resource, Workflow
from socm.planner import HeftPlanner, PlanEntry
from socm.resources import TigerResource


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
    dag = DAG()
    for i in range(8):
        dag.add_workflow(Workflow(
            name=f"W{i+1}", executable="exe", context="ctx", subcommand="sub", id=i + 1
        ))
    campaign = Campaign(id=0, workflows=dag, deadline= "50d")
    actual_plan = [
        PlanEntry(workflow=Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1, environment=None), cores=range(64, 128), memory=2000, start_time=0, end_time=45),
        PlanEntry(workflow=Workflow(name="W2", executable="exe", context="ctx", subcommand="sub", id=2, environment=None), cores=range(128, 144), memory=15000, start_time=0, end_time=25),
        PlanEntry(workflow=Workflow(name="W3", executable="exe", context="ctx", subcommand="sub", id=3, environment=None), cores=range(0, 1), memory=2000, start_time=0, end_time=560),
        PlanEntry(workflow=Workflow(name="W4", executable="exe", context="ctx", subcommand="sub", id=4, environment=None), cores=range(16, 24), memory=32000, start_time=0, end_time=140),
        PlanEntry(workflow=Workflow(name="W5", executable="exe", context="ctx", subcommand="sub", id=5, environment=None), cores=range(8, 16), memory=1000, start_time=0, end_time=145),
        PlanEntry(workflow=Workflow(name="W6", executable="exe", context="ctx", subcommand="sub", id=6, environment=None), cores=range(112, 224), memory=20000, start_time=45, end_time=55),
        PlanEntry(workflow=Workflow(name="W7", executable="exe", context="ctx", subcommand="sub", id=7, environment=None), cores=range(168, 224), memory=6000, start_time=0, end_time=20),
        PlanEntry(workflow=Workflow(name="W8", executable="exe", context="ctx", subcommand="sub", id=8, environment=None), cores=range(32, 64), memory=1000, start_time=0, end_time=30),
    ]
    planner = HeftPlanner(None, None, None)
    planner._logger = MagicMock()
    planner._estimated_memory = list()

    planner._resource_requirements = {
        1: {"req_cpus": 64, "req_memory": 2000, "req_walltime": 45},
        2: {"req_cpus": 16, "req_memory": 15000, "req_walltime": 25},
        3: {"req_cpus": 1, "req_memory": 2000, "req_walltime": 560},
        4: {"req_cpus": 8, "req_memory": 32000, "req_walltime": 140},
        5: {"req_cpus": 8, "req_memory": 1000, "req_walltime": 145},
        6: {"req_cpus": 112, "req_memory": 20000, "req_walltime": 10},
        7: {"req_cpus": 56, "req_memory": 6000, "req_walltime": 20},
        8: {"req_cpus": 32, "req_memory": 1000, "req_walltime": 30},
    }

    planner._campaign = campaign
    planner._resources = Resource(
        name="tiger3",
        nodes=2,
        cores_per_node=112,
        memory_per_node=64 * 1024,  # in MB
    )
    planner._num_oper = [1, 2, 3, 4, 5, 6, 7, 8]
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

    dag = DAG()
    for workflow in workflows:
        dag.add_workflow(workflow)
    campaign = Campaign(id=0, workflows=dag, deadline= "50d")
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
    planner._logger = MagicMock()
    planner._estimated_memory = list()

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

    planner._campaign = campaign
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
def test_plan_with_dag_dependencies(mocked_init):
    """Test that the planner schedules dependent workflows after their predecessors."""
    dag = DAG()
    for w in [
        Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1),
        Workflow(name="W2", executable="exe", context="ctx", subcommand="sub", id=2),
        Workflow(name="W3", executable="exe", context="ctx", subcommand="sub", id=3),
        Workflow(name="W4", executable="exe", context="ctx", subcommand="sub", id=4),
    ]:
        dag.add_workflow(w)
    dag.add_dependency(parent_id=1, child_id=2)
    dag.add_dependency(parent_id=1, child_id=3)

    campaign = Campaign(id=0, workflows=dag, deadline="50d")


    actual_plan = [
        PlanEntry(workflow=Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1), cores=range(0, 224), memory=2000, start_time=0, end_time=45),
        PlanEntry(workflow=Workflow(name="W2", executable="exe", context="ctx", subcommand="sub", id=2), cores=range(112, 224), memory=2000, start_time=45, end_time=75),
        PlanEntry(workflow=Workflow(name="W3", executable="exe", context="ctx", subcommand="sub", id=3), cores=range(0, 112), memory=2000, start_time=70, end_time=90),
        PlanEntry(workflow=Workflow(name="W4", executable="exe", context="ctx", subcommand="sub", id=4), cores=range(0, 112), memory=2000, start_time=45, end_time=70),
    ]

    planner = HeftPlanner(None, None, None)
    planner._logger = MagicMock()
    planner._estimated_memory = list

    planner._resource_requirements = {
        1: {"req_cpus": 224, "req_memory": 2000, "req_walltime": 45},
        2: {"req_cpus": 112, "req_memory": 2000, "req_walltime": 30},
        3: {"req_cpus": 112, "req_memory": 2000, "req_walltime": 20},
        4: {"req_cpus": 112, "req_memory": 2000, "req_walltime": 25},
    }

    planner._campaign = campaign
    planner._resources = Resource(
        name="tiger3",
        nodes=2,
        cores_per_node=112,
        memory_per_node=64 * 1024,  # in MB
    )
    planner._num_oper = [1, 2, 3, 4]
    est_plan, _ = planner._calculate_plan()

    assert est_plan == actual_plan


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

    requirements = planner._initialize_resource_estimates(resource_requirements, widxs=[1,2])

    assert requirements["estimated_walltime"] == [45, 25]
    assert requirements["estimated_cpus"] == [64, 16]
    assert requirements["estimated_memory"] == [2000, 15000]


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_get_sorted_workflow_indices(mocked_init):
    """Test that workflows are sorted by execution time (longest first)."""
    planner = HeftPlanner(None, None, None)
    planner._estimated_walltime = [45, 25, 560, 140, 145]

    sorted_indices = planner._get_sorted_workflow_indices(planner._estimated_walltime)

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
def test_find_best_resource_slot_respects_earlier_start(mocked_init):
    """Test that _find_best_resource_slot respects the earlier_start constraint.

    Setup:
      4 cores, cpus_required=2, walltime=10
      resource_free = [0, 0, 30, 30]  (cores 0-1 free now, cores 2-3 free at t=30)
      earlier_start = 20  (dependency constraint)

    Without fix (bug):
      slice 0-1: start_candidate = 0, end = 10  ← would be picked (violates dependency!)
      slice 2-3: start_candidate = 30, end = 40

    With fix:
      slice 0-1: start_candidate = max(0, 20) = 20, end = 30  ← correctly picked
      slice 2-3: start_candidate = max(30, 20) = 30, end = 40
    """
    planner = HeftPlanner(None, None, None)
    planner._logger = MagicMock()
    planner._plan = []
    planner._resources = Resource(
        name="test",
        nodes=1,
        cores_per_node=4,
        memory_per_node=10000,
    )

    resource_requirements = {
        "estimated_walltime": [10.0],
        "estimated_cpus": [2],
        "estimated_memory": [100.0],
    }
    resources = range(4)
    resource_free = np.array([0.0, 0.0, 30.0, 30.0])
    earlier_start = 20.0

    best_core_idx, start_time = planner._find_best_resource_slot(
        workflow_idx=0,
        resource_requirements=resource_requirements,
        resources=resources,
        resource_free=resource_free,
        earlier_start=earlier_start,
    )

    # Cores 0-1 are the best slot: they become free at t=0 but earliest we can
    # start is t=20 (dependency), giving end=30 — better than cores 2-3 (end=40).
    assert best_core_idx == 0
    assert np.isclose(start_time, 20.0), f"Expected start_time=20.0, got {start_time}"


@mock.patch.object(HeftPlanner, "__init__", return_value=None)
def test_calculate_plan_dependency_not_violated_by_idle_cores(mocked_init):
    """Test that a dependent workflow is not scheduled before its predecessor finishes,
    even when other cores are completely idle.

    W1 (2 cores, walltime=20) has no dependencies.
    W2 (2 cores, walltime=10) depends on W1.

    With 4 cores, cores 2-3 are idle throughout W1's execution. Without the
    earlier_start fix, the planner would schedule W2 on cores 2-3 at t=0,
    violating the W1 → W2 dependency. With the fix, W2 must start at t=20.
    """
    dag = DAG()
    w1 = Workflow(name="W1", executable="exe", context="ctx", subcommand="sub", id=1)
    w2 = Workflow(
        name="W2", executable="exe", context="ctx", subcommand="sub", id=2,
        depends=["W1"]
    )
    dag.add_workflow(w1)
    dag.add_workflow(w2)
    dag.add_dependency(parent_id=1, child_id=2)

    campaign = Campaign(id=0, workflows=dag, deadline="50d")

    planner = HeftPlanner(None, None, None)
    planner._logger = MagicMock()
    planner._estimated_memory = []
    planner._resource_requirements = {
        1: {"req_cpus": 2, "req_memory": 100, "req_walltime": 20},
        2: {"req_cpus": 2, "req_memory": 100, "req_walltime": 10},
    }
    planner._campaign = campaign
    planner._resources = Resource(
        name="test",
        nodes=1,
        cores_per_node=4,
        memory_per_node=10000,
    )

    est_plan, _ = planner._calculate_plan(
        campaign=dag,
        resources=range(4),
        resource_requirements=planner._resource_requirements,
    )

    w1_entry = next(e for e in est_plan if e.workflow.name == "W1")
    w2_entry = next(e for e in est_plan if e.workflow.name == "W2")

    assert np.isclose(w1_entry.start_time, 0.0)
    assert np.isclose(w1_entry.end_time, 20.0)
    # W2 must not start before W1 finishes
    assert w2_entry.start_time >= w1_entry.end_time, (
        f"W2 started at {w2_entry.start_time} before W1 finished at {w1_entry.end_time}"
    )
    assert np.isclose(w2_entry.start_time, 20.0)
    assert np.isclose(w2_entry.end_time, 30.0)


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

    suitable = planner._find_suitable_qos_policies(requested_cores=10)
    assert suitable == QosPolicy(name="vshort", max_walltime=30, max_jobs=10, max_cores=100)
    suitable = planner._find_suitable_qos_policies(requested_cores=110)
    assert suitable == QosPolicy(name="short", max_walltime=60, max_jobs=20, max_cores=200)
    suitable = planner._find_suitable_qos_policies(requested_cores=210)
    assert suitable == QosPolicy(name="medium", max_walltime=120, max_jobs=15, max_cores=300)
    suitable = planner._find_suitable_qos_policies(requested_cores=310)
    assert suitable == QosPolicy(name="long", max_walltime=240, max_jobs=10, max_cores=400)
    with pytest.raises(ValueError):
        planner._find_suitable_qos_policies(requested_cores=410)
