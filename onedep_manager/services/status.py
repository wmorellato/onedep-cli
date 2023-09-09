from enum import Enum, auto
from dataclasses import dataclass


class Status(Enum):
    RUNNING = "running"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


@dataclass
class InstanceStatus:
    hostname: str
    status: Status
