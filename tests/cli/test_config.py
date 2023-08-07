import os
import pytest
from click.testing import CliRunner
from unittest import mock

from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
from onedep_manager.cli.config import get, rebuild


@pytest.fixture
def mock_config(monkeypatch):
    mc = {
        "GASCOGNE": "father",
        "EILEEN": "crow",
    }

    monkeypatch.setattr(ConfigInfoData, "getConfigDictionary", lambda s: mc)


def test_valid_variable(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["gascogne"])

    assert result.exit_code == 0
    assert result.output == "GASCOGNE: father\n"


def test_missing_variable(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["bar"])

    assert result.exit_code == 0
    assert result.output == "BAR: None\n"


def test_multiple_variables(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["gascogne", "eileen"])

    assert result.exit_code == 0
    assert result.output == "GASCOGNE: father\nEILEEN: crow\n"


@mock.patch.dict(os.environ, {"TOP_WWPDB_SITE_CONFIG_DIR": "tests/fixtures/site-config/"})
def test_rebuild():
    runner = CliRunner()
    result = runner.invoke(rebuild, ["pdbe_test", "pdbe"])

    assert result.exit_code == 0
    assert os.path.exists("tests/fixtures/site-config/pdbe/pdbe_test/ConfigInfoFileCache.json")

    os.remove("tests/fixtures/site-config/pdbe/pdbe_test/ConfigInfoFileCache.json")
    os.remove("tests/fixtures/site-config/pdbe/pdbe_test/ConfigInfoFileCache.py")
