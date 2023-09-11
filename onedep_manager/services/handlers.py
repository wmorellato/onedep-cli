from abc import ABC, abstractmethod

from onedep_manager.config import Config
from onedep_manager.services.status import Status


class Handler(ABC):
    def __init__(self, config: Config) -> None:
        self._config = config

    @abstractmethod
    def start(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def stop(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def restart(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def status(self) -> Status:
        raise NotImplementedError()
