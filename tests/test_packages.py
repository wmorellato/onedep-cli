import pytest
import subprocess

from onedep_manager.schemas import PackageDistribution
from onedep_manager.packages import get_wwpdb_packages, switch_reference


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


def test_get_single_package(monkeypatch):
    package1 = MockDistribution("wwpdb.utils.config", "0.1.0", "/foo/bar/wwpdb.utils.config/wwpdb.utils.config.egg-info")
    package2 = MockDistribution("wwpdb.utils.foobar", "0.2.0", "/foo/bar/wwpdb.utils.foobar/wwpdb.utils.foobar.egg-info")

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [package1, package2]
    )

    packages = list(get_wwpdb_packages(name="wwpdb.utils.config"))

    assert len(packages) == 1
    assert packages[0].name == "wwpdb.utils.config"
    assert packages[0].version == "0.1.0"
    assert packages[0].path == "/foo/bar/wwpdb.utils.config"


def test_get_with_patterns(monkeypatch):
    package1 = MockDistribution("wwpdb.utils.config", "0.1.0", "/foo/bar/wwpdb.utils.config/wwpdb.utils.config.egg-info")
    package2 = MockDistribution("wwpdb.utils.foobar", "0.2.0", "/foo/bar/wwpdb.utils.foobar/wwpdb.utils.foobar.egg-info")
    package3 = MockDistribution("wwpdb.apps.foobar", "0.2.0", "/foo/bar/wwpdb.apps.foobar/wwpdb.apps.foobar.egg-info")

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [package1, package2, package3]
    )

    packages = list(get_wwpdb_packages(name="wwpdb.utils"))
    assert len(packages) == 2


def test_branch(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    egg = d / "wwpdb.utils.config.egg-info"
    egg.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "checkout", "-b", "foobar"], cwd=d)

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [MockDistribution("wwpdb.utils.config", "0.1.0", str(egg))]
    )

    package = next(get_wwpdb_packages(branch=True))

    assert package.branch == "foobar"


def test_detached_head(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    egg = d / "wwpdb.utils.config.egg-info"
    egg.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Second commit"], cwd=d)
    subprocess.run(["git", "checkout", "HEAD~1"], cwd=d)

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [MockDistribution("wwpdb.utils.config", "0.1.0", str(egg))]
    )

    package = next(get_wwpdb_packages(branch=True))
    assert package.branch == "HEAD"


def test_checkout(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    d.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=d)
    subprocess.run(["git", "checkout", "-b", "develop"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Second commit"], cwd=d)
    subprocess.run(["git", "checkout", "main"], cwd=d)

    package = PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path=d, branch="main")
    success = switch_reference(package=package, reference="develop")

    assert success == True

    # check the branch with actual git
    assert subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=d, capture_output=True).stdout.decode().strip() == "develop"


def test_invalid_branch(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    egg = d / "wwpdb.utils.config.egg-info"
    egg.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=d)

    package = PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path=d, branch="main")
    success = switch_reference(package=package, reference="foobar")

    assert success == False
