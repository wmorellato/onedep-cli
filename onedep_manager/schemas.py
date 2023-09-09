from enum import Enum
from dataclasses import dataclass


@dataclass
class Service:
    name: str
    description: str
    handler: str
    hosts: list
