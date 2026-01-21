"""Tests for socm CLI that don't require radical.pilot."""

import pytest


class TestCLIHelp:
    """Test that CLI help works without radical.pilot installed."""

    def test_parser_structure(self):
        """Test that the argument parser is correctly structured."""
        from socm.__main__ import get_parser

        parser = get_parser()

        # Check subparsers exist
        assert parser._subparsers is not None

        # Parse help flag to verify parser works
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_main_help_output(self, capsys):
        """Test that main --help output contains expected content."""
        from socm.__main__ import get_parser

        parser = get_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Run the SO campaign" in captured.out
        assert "lat-mapmaking" in captured.out

    def test_subcommand_help_output(self, capsys):
        """Test that lat-mapmaking --help output contains expected content."""
        from socm.__main__ import get_parser

        parser = get_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["lat-mapmaking", "--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--toml" in captured.out
        assert "--dry-run" in captured.out

    def test_subcommand_parser_arguments(self):
        """Test that lat-mapmaking subcommand has correct arguments."""
        from socm.__main__ import get_parser

        parser = get_parser()

        # Parse with required args to check structure
        args = parser.parse_args(["lat-mapmaking", "-t", "test.toml"])
        assert args.toml == "test.toml"
        assert args.dry_run is False

    def test_dry_run_flag(self):
        """Test that dry-run flag is correctly parsed."""
        from socm.__main__ import get_parser

        parser = get_parser()

        args = parser.parse_args(["lat-mapmaking", "-t", "test.toml", "--dry-run"])
        assert args.dry_run is True

    def test_no_radical_import_at_parser_level(self):
        """Test that importing the parser doesn't trigger radical imports."""
        # This test verifies that we can import and use the parser
        # without radical.pilot being available (lazy import pattern)
        from socm.__main__ import get_parser
        from socm.execs import SUBCOMMANDS

        # These should work without radical
        parser = get_parser()
        assert "lat-mapmaking" in SUBCOMMANDS
        assert parser is not None
