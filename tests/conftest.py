"""Fixtures for testing."""
from unittest.mock import Mock
import pytest

import ynca


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_receiver(hass):
    """Create a mocked Receiver instance."""
    receiver = Mock(
        spec=ynca.Receiver,
    )

    receiver.inputs = {"INPUT_ID_1": "Input Name 1", "INPUT_ID_2": "Input Name 2"}

    return receiver
