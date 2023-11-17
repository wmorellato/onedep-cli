from dataclasses import dataclass, field


@dataclass
class Service:
    name: str
    description: str
    handler: str
    hosts: list


@dataclass
class PackageDistribution:
    name: str
    version: str
    path: str
    branch: str = None
    editable: bool = False
