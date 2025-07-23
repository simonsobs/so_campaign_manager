"""Tests for socm package initialization and version handling."""

import pytest


def test_socm_version_import():
    """Test that socm package imports correctly and has version."""
    import socm
    assert hasattr(socm, '__version__')
    assert isinstance(socm.__version__, str)
    assert len(socm.__version__) > 0


def test_socm_version_format():
    """Test that version follows expected format."""
    import socm
    version = socm.__version__
    
    # Should be a string with at least major.minor.patch format
    parts = version.split('.')
    assert len(parts) >= 3
    
    # First three parts should be numeric
    for i in range(3):
        assert parts[i].isdigit(), f"Version part {i} ({parts[i]}) is not numeric"


def test_socm_module_attributes():
    """Test that socm module has expected attributes."""
    import socm
    
    # Should have __version__ attribute
    assert hasattr(socm, '__version__')
    
    # Should be a proper module
    assert hasattr(socm, '__name__')
    assert socm.__name__ == 'socm'