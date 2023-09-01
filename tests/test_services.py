import sys
import pytest

from onedep_manager.services import Dispatcher
from onedep_manager.config import Config


class HandlerTest:
    def start(self):
        print("service started succesfully")
        return "running"


def test_start_service():
    # hack to make sure we can import this module
    sys.modules["tests.test_services"] = sys.modules[__name__]

    config = Config(config_file="tests/fixtures/config.yaml")
    dispatcher = Dispatcher(config=config, local=True)
    dispatcher.start_service("apache")

    with pytest.raises(Exception):
        # foo not in config
        dispatcher.start_service("foo")

    with pytest.raises(Exception):
        # service2 in config, but invalid config
        dispatcher.start_service("service2")
