from enum import Enum, auto
from dataclasses import dataclass


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
