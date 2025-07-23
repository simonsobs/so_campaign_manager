"""Tests for socm.utils.const module."""

import pytest
from socm.utils.const import PERFORMANCE_QUERY


def test_performance_query_exists():
    """Test that PERFORMANCE_QUERY constant exists and is a string."""
    assert isinstance(PERFORMANCE_QUERY, str)
    assert len(PERFORMANCE_QUERY) > 0


def test_performance_query_content():
    """Test that PERFORMANCE_QUERY contains expected SQL elements."""
    query = PERFORMANCE_QUERY
    
    # Check for expected SQL keywords
    assert "SELECT" in query
    assert "FROM" in query
    assert "WHERE" in query
    
    # Check for expected column names
    assert "memory_function" in query
    assert "memory_param" in query
    assert "time_function" in query
    assert "time_param" in query
    
    # Check for expected table name
    assert "workflow_perf" in query
    
    # Check for expected parameters
    assert ":workflow_name" in query
    assert ":subcommand" in query


def test_performance_query_formatting():
    """Test that PERFORMANCE_QUERY is properly formatted."""
    query = PERFORMANCE_QUERY
    
    # Should contain newlines for formatting
    assert "\n" in query
    
    # Should not be empty after stripping
    assert query.strip() != ""