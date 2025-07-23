"""Tests for socm.utils.states module."""

import pytest
from socm.utils.states import (
    NEW, PLANNING, EXECUTING, DONE, FAILED, CANCELED, CFINAL, state_dict
)


def test_state_constants_exist():
    """Test that all state constants are defined."""
    assert NEW == 0
    assert PLANNING == 1
    assert EXECUTING == 2
    assert DONE == 3
    assert FAILED == 4
    assert CANCELED == 5


def test_state_constants_are_integers():
    """Test that all state constants are integers."""
    states = [NEW, PLANNING, EXECUTING, DONE, FAILED, CANCELED]
    for state in states:
        assert isinstance(state, int)


def test_state_constants_are_unique():
    """Test that all state constants have unique values."""
    states = [NEW, PLANNING, EXECUTING, DONE, FAILED, CANCELED]
    assert len(states) == len(set(states))


def test_cfinal_contains_final_states():
    """Test that CFINAL contains the expected final states."""
    assert DONE in CFINAL
    assert FAILED in CFINAL
    assert CANCELED in CFINAL
    
    # Should only contain final states
    assert len(CFINAL) == 3


def test_cfinal_does_not_contain_active_states():
    """Test that CFINAL does not contain active states."""
    assert NEW not in CFINAL
    assert PLANNING not in CFINAL
    assert EXECUTING not in CFINAL


def test_state_dict_exists():
    """Test that state_dict exists and is a dictionary."""
    assert isinstance(state_dict, dict)


def test_state_dict_completeness():
    """Test that state_dict contains all states."""
    expected_states = {
        0: "NEW",
        1: "PLANNING", 
        2: "EXECUTING",
        3: "DONE",
        4: "FAILED",
        5: "CANCELED"
    }
    
    assert state_dict == expected_states


def test_state_dict_keys_match_constants():
    """Test that state_dict keys match the state constants."""
    assert state_dict[NEW] == "NEW"
    assert state_dict[PLANNING] == "PLANNING"
    assert state_dict[EXECUTING] == "EXECUTING"
    assert state_dict[DONE] == "DONE"
    assert state_dict[FAILED] == "FAILED"
    assert state_dict[CANCELED] == "CANCELED"


def test_state_dict_values_are_strings():
    """Test that all state_dict values are strings."""
    for value in state_dict.values():
        assert isinstance(value, str)
        assert len(value) > 0


def test_state_dict_values_are_uppercase():
    """Test that all state_dict values are uppercase."""
    for value in state_dict.values():
        assert value == value.upper()