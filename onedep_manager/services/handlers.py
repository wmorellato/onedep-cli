import sys
from abc import ABC, abstractmethod

from onedep_manager.config import Config
from onedep_manager.services.schemas import Status, Commands


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


class Parser:
    def __init__(self, handler: Handler) -> None:
        self._handler = handler
    
    def run(self) -> Status:
        command = Commands(sys.argv[1])

        if command == Commands.START:
            return self._handler.start()
        elif command == Commands.STOP:
            return self._handler.stop()
        elif command == Commands.RESTART:
            return self._handler.restart()
        elif command == Commands.STATUS:
            return self._handler.status()
