import pytest

from onedep_manager.schemas import PackageDistribution
from onedep_manager.packages import get_wwpdb_packages


class MockDistribution:
    def __init__(self, name, version, path):
        self.metadata = {
            "Name": name,
            "Version": version
        }
        self._path = path


def test_get_wwpdb_packages(monkeypatch):
    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [MockDistribution("wwpdb.utils.config", "0.1.0", "/foo/bar/wwpdb.utils.config/wwpdb.utils.config.egg-info")]
    )

    package = next(get_wwpdb_packages())

    assert package.name == "wwpdb.utils.config"
    assert package.version == "0.1.0"
    assert package.path == "/foo/bar/wwpdb.utils.config"
