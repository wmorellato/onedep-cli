import sys
import logging
import pytest
import socket
from unittest.mock import MagicMock

from onedep_manager.services.dispatcher import LocalDispatcher, RemoteDispatcher
from onedep_manager.services.schemas import Status
from onedep_manager.schemas import Service
from onedep_manager.config import Config
from onedep_manager.exceptions import ServiceNotFoundError, HandlerLoadError


class HandlerTest:
    def __init__(self, config):
        self._config = config

    def start(self):
        print("service started succesfully")
        return Status.RUNNING


class FailingHandlerTest:
    def __init__(self, config):
        self._config = config

    def start(self):
        raise RuntimeError("boom")


def test_local_dispatcher():
    # hack to make sure we can import this module
    sys.modules["tests.test_services"] = sys.modules[__name__]

    config = Config(config_file="tests/fixtures/config.yaml")
    dispatcher = LocalDispatcher(config=config)
    status = dispatcher.start_service("apache")

    assert status[0].hostname == socket.gethostname()
    assert status[0].status == Status.RUNNING

    with pytest.raises(HandlerLoadError):
        # "foo" is in config, but its handler class (FooTest) doesn't exist
        dispatcher.start_service("foo")

    with pytest.raises(ServiceNotFoundError):
        # "service2" is not in config at all
        dispatcher.start_service("service2")


def test_local_dispatcher_logs_and_reports_failed_on_handler_error(monkeypatch, caplog):
    # same trick as test_local_dispatcher: fake the module path so the
    # dynamically-loaded handler class resolves.
    sys.modules["tests.test_services"] = sys.modules[__name__]

    config = Config(config_file="tests/fixtures/config.yaml")
    monkeypatch.setattr(
        config,
        "get_service",
        lambda name: Service(name="failing", description="", handler="tests.test_services.FailingHandlerTest", hosts=["localhost"]),
    )

    dispatcher = LocalDispatcher(config=config)

    with caplog.at_level(logging.ERROR):
        status = dispatcher.start_service("failing")

    assert status[0].status == Status.FAILED
    assert any("failing" in record.getMessage() for record in caplog.records)


def test_remote_dispatcher(monkeypatch):
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"running"

    mock_ssh = MagicMock()
    mock_ssh.return_value.exec_command.return_value = (None, mock_stdout, None)
    monkeypatch.setattr("onedep_manager.services.dispatcher.SSHClient", mock_ssh)

    config = Config(config_file="tests/fixtures/config.yaml")
    dispatcher = RemoteDispatcher(config=config)
    status = dispatcher.start_service("apache")

    assert status[0].hostname == "localhost"
    assert status[0].status == Status.RUNNING
