from unittest import mock
import pytest

from ops.testing import Harness
from ops.model import MaintenanceStatus, BlockedStatus

from governor.base import GovernorBase


@pytest.fixture
def harness():
    return Harness(
        GovernorBase,
        actions="""
        governor-event:
            description: ''
        """,
    )


def test_base_blocked(harness):
    mkdir_patcher = mock.patch("os.makedirs")
    storage_patcher = mock.patch("sqlite3.connect")
    mkdir_patcher.start()
    storage_patcher.start()
    harness.set_leader(True)
    harness.set_model_name("test")
    harness.begin_with_initial_hooks()
    assert isinstance(harness.charm.model.unit.status, BlockedStatus)
    storage_patcher.stop()


@mock.patch("governor.juju_wrapper.JujuConnection.__init__")
def test_base(mock_juju_connection, harness):
    mkdir_patcher = mock.patch("os.makedirs")
    storage_patcher = mock.patch("sqlite3.connect")
    mkdir_patcher.start()
    storage_patcher.start()
    mock_juju_connection.return_value = None

    harness.set_leader(True)
    harness.set_model_name("test")
    harness.update_config(
        {
            "juju_controller_address": "address",
            "juju_controller_user": "user",
            "juju_controller_password": "password",
            "juju_controller_cacert": "cacert",
        }
    )
    harness.begin_with_initial_hooks()
    assert isinstance(harness.charm.model.unit.status, MaintenanceStatus)
