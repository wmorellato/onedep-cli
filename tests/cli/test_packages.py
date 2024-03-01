import pytest
from click.testing import CliRunner

from onedep_manager.cli.packages import get, update, install
from onedep_manager.schemas import PackageDistribution

from wwpdb.utils.config.ConfigInfoData import ConfigInfoData


@pytest.fixture
def mock_config(monkeypatch):
    mc = {
        "TOP_SOFTWARE_DIR": "/top/dir"
    }

    monkeypatch.setattr(ConfigInfoData, "getConfigDictionary", lambda s: mc)


def test_get(monkeypatch, mock_config):
    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_wwpdb_packages",
        lambda name=None, branch=None: [
            PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar/wwpdb.utils.config", branch="master"),
            PackageDistribution(name="wwpdb.utils.foobar", version="0.2.0", path="/top/dir/wwpdb.utils.foobar")
        ]
    )

    runner = CliRunner()
    result = runner.invoke(get, ["all"])

    assert result.exit_code == 0
    assert "wwpdb.utils.config" in result.output
    assert "0.1.0" in result.output
    assert "/foo/bar/wwpdb.utils.config" in result.output
    assert "master" in result.output

    assert "wwpdb.utils.foobar" in result.output
    assert "0.2.0" in result.output
    assert "${TOP_SOFTWARE_DIR}/wwpdb.utils" in result.output


def test_update(monkeypatch, mock_config):
    monkeypatch.setattr(
        "onedep_manager.cli.packages.pull",
        lambda package: True,
    )

    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_package",
        lambda name=None, branch=None: PackageDistribution(name="wwpdb.utils.config", version="0.2.0", path="/foo/bar/wwpdb.utils.config", branch="master"),
    )

    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_wwpdb_packages",
        lambda name=None, branch=None: [
            PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar/wwpdb.utils.config", branch="master"),
        ]
    )

    runner = CliRunner()
    result = runner.invoke(update, ["config"])
    print(result.output)

    assert result.exit_code == 0
    assert "0.1.0 -> 0.2.0" in result.output


def test_install_dev(monkeypatch, mock_config):
    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_package",
        lambda name=None, branch=None: PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar/wwpdb.utils.config", branch="master"),
    )

    monkeypatch.setattr("onedep_manager.packages.clone",
                        lambda package_name, reference="develop": "/foo/bar/wwpdb.utils.config")

    runner = CliRunner()
    result = runner.invoke(install, ["-d", "wwpdb.utils.config"])
    print(result.output)

    assert result.exit_code == 0
    assert "wwpdb.utils.config" in result.output
    assert "0.1.0" in result.output
    assert "/foo/bar/wwpdb.utils.config" in result.output
    assert "master" in result.output


def test_install(monkeypatch, mock_config):
    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_package",
        lambda name=None, branch=None: PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar/wwpdb.utils.config"),
    )

    monkeypatch.setattr("onedep_manager.packages.clone",
                        lambda package_name, reference="develop": "/foo/bar/wwpdb.utils.config")

    runner = CliRunner()
    result = runner.invoke(install, ["wwpdb.utils.config"])
    print(result.output)

    assert result.exit_code == 0
    assert "wwpdb.utils.config" in result.output
    assert "0.1.0" in result.output
    assert "/foo/bar/wwpdb.utils.config" in result.output
    assert "master" not in result.output
