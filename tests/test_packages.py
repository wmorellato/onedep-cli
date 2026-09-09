import os
import subprocess
from unittest.mock import MagicMock

from onedep_manager.schemas import PackageDistribution
from onedep_manager.packages import get_wwpdb_packages, switch_reference, pull, clone, install_package, setup_pip_env


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

    assert success

    # check the branch with actual git
    assert subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=d, capture_output=True).stdout.decode().strip() == "develop"


def test_invalid_branch(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    d.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=d)

    package = PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path=d, branch="main")
    success = switch_reference(package=package, reference="foobar")

    assert not success


def test_update(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    d.mkdir(parents=True)

    mock_repo = MagicMock()
    mock_repo.git.pull = lambda *args, **kwargs: None

    monkeypatch.setattr("onedep_manager.packages.git.Repo", mock_repo)
    monkeypatch.setattr("onedep_manager.packages.install_package", lambda source, edit: True)

    subprocess.run(["git", "init"], cwd=d)

    package = PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path=d, branch="main")
    success = pull(package=package)

    assert success


def test_dirty(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    egg = d / "wwpdb.utils.config.egg-info"
    egg.mkdir(parents=True)

    tracked_file = d / "setup.py"
    tracked_file.write_text("original")

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "add", "setup.py"], cwd=d)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=d)

    tracked_file.write_text("modified")

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [MockDistribution("wwpdb.utils.config", "0.1.0", str(egg))]
    )

    package = next(get_wwpdb_packages(branch=True))

    assert package.dirty is True
    assert "*" not in package.branch


def test_clean_repo_is_not_dirty(monkeypatch, tmp_path):
    d = tmp_path / "wwpdb.utils.config"
    egg = d / "wwpdb.utils.config.egg-info"
    egg.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=d)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=d)

    monkeypatch.setattr(
        "onedep_manager.packages.metadata.distributions",
        lambda: [MockDistribution("wwpdb.utils.config", "0.1.0", str(egg))]
    )

    package = next(get_wwpdb_packages(branch=True))

    assert package.dirty is False


def test_pull_uses_clean_branch_not_dirty_marker(monkeypatch):
    mock_repo_instance = MagicMock()
    mock_repo_cls = MagicMock(return_value=mock_repo_instance)

    monkeypatch.setattr("onedep_manager.packages.git.Repo", mock_repo_cls)

    # branch is already the clean ref name; dirty is tracked separately and
    # must never be concatenated into the string used as a git ref.
    package = PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar", branch="develop", dirty=True)
    success = pull(package=package)

    assert success is True
    mock_repo_instance.git.pull.assert_called_once_with("origin", "develop")


def test_clone_clones_into_a_package_specific_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("onedep_manager.packages.Config.from_site", lambda self, variable: str(tmp_path))

    cloned_paths = []

    def fake_clone_from(url, to_path):
        cloned_paths.append(to_path)
        os.makedirs(to_path, exist_ok=True)
        return MagicMock()

    monkeypatch.setattr("onedep_manager.packages.git.Repo.clone_from", fake_clone_from)

    path1 = clone("wwpdb.utils.config")
    path2 = clone("wwpdb.utils.dp")

    assert path1 == os.path.join(str(tmp_path), "source", "wwpdb.utils.config")
    assert path2 == os.path.join(str(tmp_path), "source", "wwpdb.utils.dp")
    assert path1 != path2
    assert os.path.isdir(path1)
    assert os.path.isdir(path2)
    assert cloned_paths == [path1, path2]


def test_install_package_checks_returncode(monkeypatch):
    fake_result = MagicMock(returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr("onedep_manager.packages.subprocess.run", lambda *args, **kwargs: fake_result)

    success = install_package("wwpdb.utils.config")

    assert success is False


def test_setup_pip_env_checks_returncode(monkeypatch):
    fake_result = MagicMock(returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr("onedep_manager.packages.subprocess.run", lambda *args, **kwargs: fake_result)

    success = setup_pip_env("user", "pass", "https://example.com")

    assert success is False
