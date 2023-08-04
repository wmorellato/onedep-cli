import pytest
from click.testing import CliRunner

from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
from onedep_manager.cli.config import get


@pytest.fixture
def mock_config(monkeypatch):
    # cid_mock = MagicMock(ConfigInfoData)
    mc = {
        "gascogne": "father",
        "eileen": "crow",
    }

    monkeypatch.setattr(ConfigInfoData, "getConfigDictionary", lambda s: mc)


def test_valid_variable(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["gascogne"])

    assert result.exit_code == 0
    assert result.output == "gascogne: father\n"


def test_missing_variable(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["bar"])

    assert result.exit_code == 0
    assert result.output == "bar: None\n"


def test_multiple_variables(mock_config):
    runner = CliRunner()
    result = runner.invoke(get, ["gascogne", "eileen"])

    assert result.exit_code == 0
    assert result.output == "gascogne: father\neileen: crow\n"
