import shutil
import pytest
from unittest.mock import MagicMock
from click.testing import CliRunner

from onedep_manager.cli.services import start
from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
from onedep_manager.services.status import Status, InstanceStatus


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    odm_path = tmp_path / "odm"
    odm_path.mkdir(parents=True, exist_ok=True)
    shutil.copy("tests/fixtures/config.yaml", odm_path)

    mc = {
        "TOP_SOFTWARE_DIR": tmp_path
    }

    monkeypatch.setattr(ConfigInfoData, "getConfigDictionary", lambda s: mc)


def test_start_service(mock_config, monkeypatch):
    mock_dispatch = MagicMock()
    mock_dispatch.return_value.start_service.return_value = [InstanceStatus(hostname="localhost", status=Status.RUNNING)]
    monkeypatch.setattr("onedep_manager.cli.services.LocalDispatcher", mock_dispatch)

    runner = CliRunner()
    result = runner.invoke(start, ["foo", "-l"])

    assert result.exit_code == 0
    assert "localhost" in result.output
    assert "running" in result.output
