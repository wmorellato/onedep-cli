import sys
import pytest
import socket
from unittest.mock import MagicMock

from onedep_manager.services.dispatcher import LocalDispatcher, RemoteDispatcher
from onedep_manager.services.status import Status
from onedep_manager.config import Config


class HandlerTest:
    def start(self):
        print("service started succesfully")
        return "running"


def test_local_dispatcher():
    # hack to make sure we can import this module
    sys.modules["tests.test_services"] = sys.modules[__name__]

    config = Config(config_file="tests/fixtures/config.yaml")
    dispatcher = LocalDispatcher(config=config)
    status = dispatcher.start_service("apache")

    assert status[0].hostname == socket.gethostname()
    assert status[0].status == Status.RUNNING

    with pytest.raises(Exception):
        # foo not in config
        dispatcher.start_service("foo")

    with pytest.raises(Exception):
        # service2 in config, but invalid config
        dispatcher.start_service("service2")


def test_remote_dispatcher(monkeypatch):
    mock_ssh = MagicMock()
    mock_ssh.return_value.exec_command.return_value = (None, "running", None)
    monkeypatch.setattr("onedep_manager.services.dispatcher.SSHClient", mock_ssh)

    config = Config(config_file="tests/fixtures/config.yaml")
    dispatcher = RemoteDispatcher(config=config)
    status = dispatcher.start_service("apache")

    assert status[0].hostname == "localhost"
    assert status[0].status == Status.RUNNING
