from unittest import mock

import pytest


@pytest.fixture
def mock_context_act():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.workflows.ml_null_tests.base.Context") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self, context_file):
                self.obsdb = mock.Mock()

                def mock_query(query):
                    if "1551468569.1551475843.ar5_1" in query:
                        return [
                            {
                                "obs_id": "1551468569.1551475843.ar5_1",
                                "n_samples": 259584,
                                "timestamp": 1575600533,
                                "wafer_slots_list": "ws0,ws1",
                                "tube_slot": "st1",
                                "az_center": 280,
                            }
                        ]
                    return []

                self.obsdb.query = mock.Mock(side_effect=mock_query)

            def get_meta(self, obs_id):
                return mock.Mock(samps=mock.Mock(count=1000))

        # Set the side effect to use our implementation
        mocked.side_effect = MockContextImpl
        yield mocked


@pytest.fixture
def mock_context_lat():
    """Create a fixture that returns a mock Context class."""
    with mock.patch("socm.workflows.ml_null_tests.base.Context") as mocked:
        # Create the mock context behavior
        class MockContextImpl:
            def __init__(self, context_file):
                self.obsdb = mock.Mock()

                def mock_query(query):
                    if "1551468569.1551475843.ar5_1" in query:
                        return [
                            {
                                "obs_id": "1551468569.1551475843.ar5_1",
                                "n_samples": 259584,
                                "timestamp": 1575600533,
                                "wafer_slots_list": "ws0,ws1",
                                "tube_slot": "st1",
                                "az_center": 280,
                            }
                        ]
                    return []

                self.obsdb.query = mock.Mock(side_effect=mock_query)

            def get_meta(self, obs_id):
                return mock.Mock(samps=mock.Mock(count=1000))

        # Set the side effect to use our implementation
        mocked.side_effect = MockContextImpl
        yield mocked
