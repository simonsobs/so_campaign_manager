"""Tests for socm.workflows.sat_simulation module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Mock pydantic and related dependencies
mock_modules = {
    'pydantic': Mock(),
}

# Set up mock attributes
mock_modules['pydantic'].PrivateAttr = lambda default: default

# Add mocks to sys.modules before importing
for module_name, mock_module in mock_modules.items():
    sys.modules[module_name] = mock_module

# Mock the base Workflow class since we can't import it directly
class MockWorkflow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


def test_satworkflow_creation():
    """Test SATSimWorkflow creation with basic parameters."""
    # Mock the base Workflow class
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="test_executable",
            schedule="test_schedule.txt",
            bands="SAT_f150",
            wafer_slots="w50"
        )
        
        assert workflow.output_dir == "/test/output"
        assert workflow.name == "sat_sims"  # default value
        assert workflow.executable == "test_executable"
        assert workflow.schedule == "test_schedule.txt"
        assert workflow.bands == "SAT_f150"
        assert workflow.wafer_slots == "w50"


def test_satworkflow_defaults():
    """Test SATSimWorkflow with default values."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="test_executable"
        )
        
        # Check default values
        assert workflow.name == "sat_sims"
        assert workflow.executable == "test_executable"  # overridden
        assert workflow.bands == "SAT_f090"  # default
        assert workflow.wafer_slots == "w25"  # default
        assert workflow.sample_rate == 37  # default
        assert workflow.sim_noise is False  # default
        assert workflow.scan_map is False  # default
        assert workflow.sim_atmosphere is False  # default
        assert workflow.sim_sss is False  # default
        assert workflow.sim_hwpss is False  # default
        assert workflow.pixels_healpix_radec_nside == 512  # default


def test_satworkflow_get_command():
    """Test get_command method."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            subcommand="run_sim",
            resources={"ranks": 4, "threads": 8}
        )
        
        command = workflow.get_command()
        
        expected_start = "srun --cpu_bind=cores --export=ALL --ntasks-per-node=4 --cpus-per-task=8 toast_so_sim run_sim --job_group_size=4"
        assert command.startswith(expected_start)
        assert "--out /test/output" in command


def test_satworkflow_get_arguments_basic():
    """Test get_arguments method with basic parameters."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            schedule="schedule.txt",
            bands="SAT_f150",
            sample_rate=50
        )
        
        arguments = workflow.get_arguments()
        
        assert "--out /test/output" in arguments
        assert "--schedule=schedule.txt" in arguments
        assert "--bands=SAT_f150" in arguments
        assert "--sample_rate=50" in arguments


def test_satworkflow_get_arguments_excludes_internal_fields():
    """Test that get_arguments excludes internal fields."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            name="custom_name",
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            id=123,
            environment={"VAR": "value"},
            resources={"ranks": 2}
        )
        
        arguments = workflow.get_arguments()
        
        # These fields should not appear in arguments
        assert "--name=" not in arguments
        assert "--executable=" not in arguments
        assert "--id=" not in arguments
        assert "--environment=" not in arguments
        assert "--resources=" not in arguments
        
        # output_dir should be handled specially as --out
        assert "--output_dir=" not in arguments
        assert "--out /test/output" in arguments


def test_satworkflow_get_arguments_boolean_handling():
    """Test boolean argument handling."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            sim_noise=True,
            scan_map=False,
            sim_atmosphere=True
        )
        
        arguments = workflow.get_arguments()
        
        # True booleans should use .enable
        assert "--sim_noise.enable" in arguments
        assert "--sim_atmosphere.enable" in arguments
        
        # False booleans should use .disable
        assert "--scan_map.disable" in arguments


def test_satworkflow_get_arguments_file_url_handling():
    """Test file:// URL handling in arguments."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="file:///path/to/context.yaml",
            executable="toast_so_sim",
            schedule="file:///path/to/schedule.txt"
        )
        
        arguments = workflow.get_arguments()
        
        # file:// URLs should be converted to absolute paths
        assert "file://" not in arguments
        assert "/path/to/schedule.txt" in arguments


def test_satworkflow_arg_translation():
    """Test argument name translation using _arg_translation."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            sim_hwpss_atmo_data="atmo_data.h5",
            pixels_healpix_radec_nside=1024,
            filterbin_name="filterbin_test",
            processing_mask_file="mask.fits"
        )
        
        arguments = workflow.get_arguments()
        
        # These should be translated according to _arg_translation
        assert "--sim_hwpss.atmo_data=atmo_data.h5" in arguments
        assert "--pixels_healpix_radec.nside=1024" in arguments
        assert "--filterbin.name=filterbin_test" in arguments
        assert "--processing_mask.file=mask.fits" in arguments
        
        # Original names should not appear
        assert "--sim_hwpss_atmo_data=" not in arguments
        assert "--pixels_healpix_radec_nside=" not in arguments


def test_satworkflow_get_arguments_none_values():
    """Test that None values are handled correctly."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            schedule=None,
            sim_hwpss_atmo_data=None,
            filterbin_name=None
        )
        
        arguments = workflow.get_arguments()
        
        # None values should be included in arguments (as "None")
        assert "--schedule=None" in arguments
        assert "--sim_hwpss.atmo_data=None" in arguments
        assert "--filterbin.name=None" in arguments


def test_satworkflow_get_arguments_sorted_output():
    """Test that arguments are output in sorted order."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            zebra_param="last",
            alpha_param="first",
            beta_param="middle"
        )
        
        arguments = workflow.get_arguments()
        
        # Arguments should appear in alphabetical order (after --out)
        alpha_pos = arguments.find("--alpha_param=")
        beta_pos = arguments.find("--beta_param=")
        zebra_pos = arguments.find("--zebra_param=")
        
        assert alpha_pos < beta_pos < zebra_pos


def test_satworkflow_complex_boolean_combinations():
    """Test complex combinations of boolean flags."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            sim_noise=True,
            scan_map=True,
            sim_atmosphere=False,
            sim_sss=False,
            sim_hwpss=True
        )
        
        arguments = workflow.get_arguments()
        
        # Check all boolean flags
        assert "--sim_noise.enable" in arguments
        assert "--scan_map.enable" in arguments
        assert "--sim_atmosphere.disable" in arguments
        assert "--sim_sss.disable" in arguments
        assert "--sim_hwpss.enable" in arguments


def test_satworkflow_private_attributes():
    """Test that _arg_translation is properly set up."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim"
        )
        
        # Check that _arg_translation exists and has expected mappings
        expected_translations = {
            "sim_hwpss_atmo_data": "sim_hwpss.atmo_data",
            "pixels_healpix_radec_nside": "pixels_healpix_radec.nside",
            "filterbin_name": "filterbin.name",
            "processing_mask_file": "processing_mask.file",
        }
        
        assert hasattr(workflow, '_arg_translation')
        assert workflow._arg_translation == expected_translations


def test_satworkflow_get_command_strips_whitespace():
    """Test that get_command strips trailing whitespace."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim",
            subcommand="test",
            resources={"ranks": 1, "threads": 1}
        )
        
        command = workflow.get_command()
        
        # Command should not have trailing whitespace
        assert not command.endswith(" ")
        assert not command.endswith("\t")
        assert not command.endswith("\n")


def test_satworkflow_get_arguments_strips_whitespace():
    """Test that get_arguments strips trailing whitespace."""
    with patch('socm.workflows.sat_simulation.Workflow', MockWorkflow):
        from socm.workflows.sat_simulation import SATSimWorkflow
        
        workflow = SATSimWorkflow(
            output_dir="/test/output",
            context="test_context",
            executable="toast_so_sim"
        )
        
        arguments = workflow.get_arguments()
        
        # Arguments should not have trailing whitespace
        assert not arguments.endswith(" ")
        assert not arguments.endswith("\t")
        assert not arguments.endswith("\n")