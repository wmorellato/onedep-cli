import logging
import importlib

from abc import ABC
from enum import Enum
from paramiko.client import SSHClient
from paramiko.ssh_exception import SSHException

from onedep_manager.config import Config
from onedep_manager.services.status import Status

from wwpdb.utils.config.ConfigInfo import ConfigInfo, getSiteId

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Commands(Enum):
    START = "start"
    STOP = "stop"


class Dispatcher(ABC):
    def __init__(self, config: Config) -> None:
        super().__init__()

    def start_service(self, service: str):
        raise NotImplementedError()


class LocalDispatcher(Dispatcher):
    """Dispatcher for the local host. This class is NOT
    responsible for starting processes. It just calls
    the registered handler, which will then start the
    service in its current host.
    """
    def __init__(self, config: Config) -> None:
        self._config = config
    
    def _get_handler(self, handler: str) -> None:
        module, klass = handler.rsplit(".", 1)

        try:
            mod = importlib.import_module(module)
            handler = getattr(mod, klass)
            return handler
        except Exception as e:
            raise Exception(f"Could not load handler {handler}: {e}")

    def start_service(self, service: str) -> None:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)
        handler().start()


class RemoteDispatcher(Dispatcher):
    def __init__(self, config: Config) -> None:
        self._config = config
        self._ci = ConfigInfo()
        self._setup_env()
    
    def _setup_env(self):
        self.env = {
            "WWPDB_SITE_ID": getSiteId(),
            "WWPDB_SITE_LOC": self._ci.get("WWPDB_SITE_LOC"),
            "ONEDEP_PATH": self._ci.get("TOP_SOFTWARE_DIR"),
            "SITE_SUFFIX": self._ci.get("SITE_SUFFIX"),
        }

    def _run_onhost(self, host: str, module: str, command: Commands):
        client = SSHClient()
        client.load_system_host_keys()
        client.connect(host, timeout=10)

        try:
            stdin, stdout, stderr = client.exec_command(f"python -m {module} {command}", environment=self.env)
        except SSHException:
            # logger.error()
            return Status.FAILED

        if "running" not in stdout:
            return Status.FAILED

    def start_service(self, service: str):
        status = []
        serv = self._config.get_service(service)
        module, klass = serv.handler.rsplit(".", 1)

        for h in serv.hosts:
            status.append(self._run_onhost(h, module, Commands.START))

        return status
