import socket
import logging
import importlib

from abc import ABC, abstractmethod
from typing import List
from paramiko.client import SSHClient
from paramiko.ssh_exception import SSHException, AuthenticationException

from onedep_manager.config import Config
from onedep_manager.exceptions import HandlerLoadError
from onedep_manager.services.schemas import Status, InstanceStatus, Commands

from wwpdb.utils.config.ConfigInfo import ConfigInfo, getSiteId


logger = logging.getLogger(__name__)
paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.ERROR)


class Dispatcher(ABC):
    def __init__(self, config: Config) -> None:
        super().__init__()

    @abstractmethod
    def start_service(self, service: str) -> InstanceStatus:
        raise NotImplementedError()

    @abstractmethod
    def stop_service(self, service: str) -> InstanceStatus:
        raise NotImplementedError()


class LocalDispatcher(Dispatcher):
    """Dispatcher for the local host. This class is NOT
    responsible for starting processes. It just calls
    the registered handler, which will then start the
    service in its current host.
    """
    def __init__(self, config: Config) -> None:
        self._config = config
        self._hostname = socket.gethostname()
    
    def _get_handler(self, handler: str) -> None:
        module, klass = handler.rsplit(".", 1)

        try:
            mod = importlib.import_module(module)
            return getattr(mod, klass)
        except Exception as e:
            raise HandlerLoadError(f"Could not load handler {handler}: {e}") from e

    def start_service(self, service: str) -> List[InstanceStatus]:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)

        try:
            status = handler(self._config).start()
        except Exception as e:
            logger.error("Failed to start service '%s': %s", service, e, exc_info=True)
            return [InstanceStatus(hostname=self._hostname, status=Status.FAILED)]

        return [InstanceStatus(hostname=self._hostname, status=status)]

    def stop_service(self, service: str) -> InstanceStatus:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)

        try:
            status = handler(self._config).stop()
        except Exception as e:
            logger.error("Failed to stop service '%s': %s", service, e, exc_info=True)
            return [InstanceStatus(hostname=self._hostname, status=Status.FAILED)]

        return [InstanceStatus(hostname=self._hostname, status=status)]

    def restart_service(self, service: str) -> InstanceStatus:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)

        try:
            status = handler(self._config).restart()
        except Exception as e:
            logger.error("Failed to restart service '%s': %s", service, e, exc_info=True)
            return [InstanceStatus(hostname=self._hostname, status=Status.FAILED)]

        return [InstanceStatus(hostname=self._hostname, status=status)]

    def get_status(self, service: str) -> InstanceStatus:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)

        try:
            status = handler(self._config).status()
        except Exception as e:
            logger.error("Failed to get status of service '%s': %s", service, e, exc_info=True)
            return [InstanceStatus(hostname=self._hostname, status=Status.FAILED)]

        return [InstanceStatus(hostname=self._hostname, status=status)]


class RemoteDispatcher(Dispatcher):
    """Dispatcher for remote hosts. This class is NOT
    responsible for starting processes. It just calls
    the registered handler, which will then start the
    service in its current host.
    """
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

        try:
            client.connect(host, timeout=10)
            stdin, stdout, stderr = client.exec_command(f"python -m {module} {command}", environment=self.env)
        except (SSHException, AuthenticationException):
            logger.error("Couldn't connect to host %s", host, exc_info=True)
            return InstanceStatus(hostname=host, status=Status.FAILED)

        status = Status(stdout.read().decode("utf-8").strip())
        if status != Status.RUNNING:
            return InstanceStatus(hostname=host, status=Status.FAILED)

        return InstanceStatus(hostname=host, status=status)

    def start_service(self, service: str) -> List[InstanceStatus]:
        status = []
        serv = self._config.get_service(service)
        module, klass = serv.handler.rsplit(".", 1)

        for h in serv.hosts:
            status.append(self._run_onhost(h, module, Commands.START))

        return status

    def stop_service(self, service: str) -> InstanceStatus:
        status = []
        serv = self._config.get_service(service)
        module, klass = serv.handler.rsplit(".", 1)

        for h in serv.hosts:
            status.append(self._run_onhost(h, module, Commands.STOP))

        return status

    def restart_service(self, service: str) -> InstanceStatus:
        status = []
        serv = self._config.get_service(service)
        module, klass = serv.handler.rsplit(".", 1)

        for h in serv.hosts:
            status.append(self._run_onhost(h, module, Commands.RESTART))

        return status

    def get_status(self, service: str) -> InstanceStatus:
        status = []
        serv = self._config.get_service(service)
        module, klass = serv.handler.rsplit(".", 1)

        for h in serv.hosts:
            status.append(self._run_onhost(h, module, Commands.STATUS))

        return status
