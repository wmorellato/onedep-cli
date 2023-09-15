from enum import Enum
from dataclasses import dataclass


class Commands(Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    STATUS = "status"

    def __str__(self) -> str:
        return self.value


class Status(Enum):
    UNKNOWN = "unknown"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"

    def __str__(self) -> str:
        return self.value


@dataclass
class InstanceStatus:
    hostname: str
    status: Status
