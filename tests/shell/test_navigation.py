from unittest import mock

from onedep_manager.shell.app import OneDepShell
from onedep_manager.shell.resolver import EntryPathResolver


class FakePathInfo:
    def getTempDepPath(self, dataSetId):
        return f"/data/tempdep/{dataSetId}"

    def getDepositPath(self, dataSetId):
        return f"/data/deposit/{dataSetId}"

    def getDepositUIPath(self, dataSetId):
        return f"/data/deposit-ui/{dataSetId}"

    def getArchivePath(self, dataSetId):
        return f"/data/archive/{dataSetId}"

    def getDirPath(self, dataSetId, fileSource):
        return f"/data/{fileSource}/{dataSetId}"

    def getInstancePath(self, dataSetId, wfInstanceId):
        return f"/data/archive/{dataSetId}/instance/{wfInstanceId}"


def _shell(tmp_path, config=None):
    return OneDepShell(
        config=config or mock.Mock(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugin_dirs=[tmp_path / "plugins"],
        script_dirs=[tmp_path / "scripts"],
        cli_group_imports=[],
    )


def test_cd_with_explicit_identifier_chdirs_and_syncs_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "archive" / "D_800000"
    root.mkdir(parents=True)

    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(root))})())

    shell.do_cd("archive D_800000")

    import os

    assert os.getcwd() == str(root)
    assert shell.context.current_entry == "D_800000"
    assert "D_800000" in shell.prompt


def test_cd_falls_back_to_current_entry_when_identifier_omitted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_800000"
    root.mkdir(parents=True)
    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(root))})())
    shell.context.set_entry("D_800000")

    shell.do_cd("archive")

    import os

    assert os.getcwd() == str(root)


def test_cd_without_identifier_or_current_entry_reports_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)

    shell.do_cd("archive")

    output = capsys.readouterr()
    assert "Usage: cd archive" in (output.out + output.err)


def test_cd_unknown_repo_reports_clean_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)

    shell.do_cd("not-a-repo D_800000")

    output = capsys.readouterr()
    assert "Unknown repository" in (output.out + output.err)


def test_cd_missing_directory_reports_error_and_does_not_chdir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(
        path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(tmp_path / "missing"))})()
    )

    shell.do_cd("archive D_800000")

    import os

    assert os.getcwd() == str(tmp_path)
    output = capsys.readouterr()
    assert "directory not found" in (output.out + output.err)


def test_cdd_mnemonic_resolves_deposit_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "deposit" / "D_800000"
    root.mkdir(parents=True)
    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(path_info=type("PI", (), {"getDepositPath": staticmethod(lambda dataSetId: str(root))})())

    shell.do_cdd("D_800000")

    import os

    assert os.getcwd() == str(root)
    assert shell.context.current_entry == "D_800000"


def test_mnemonic_with_too_many_args_reports_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)

    shell.do_cdd("D_800000 extra")

    output = capsys.readouterr()
    assert "Usage: cdd" in (output.out + output.err)


def test_cds_uses_config_session_path_not_resolver(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sessions_root = tmp_path / "sessions"
    (sessions_root / "abc123").mkdir(parents=True)
    config = mock.Mock()
    config.from_site.return_value = str(sessions_root)
    shell = _shell(tmp_path, config=config)

    shell.do_cds("abc123")

    import os

    assert os.getcwd() == str(sessions_root / "abc123")
    config.from_site.assert_called_with("SITE_WEB_APPS_SESSIONS_PATH")


def test_cdwfi_with_one_arg_uses_current_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_800000" / "instance" / "W_001"
    root.mkdir(parents=True)
    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(
        path_info=type(
            "PI",
            (),
            {"getInstancePath": staticmethod(lambda dataSetId, wfInstanceId: str(tmp_path / "archive" / dataSetId / "instance" / wfInstanceId))},
        )()
    )
    shell.context.set_entry("D_800000")

    shell.do_cdwfi("W_001")

    import os

    assert os.getcwd() == str(root)
    assert shell.context.current_entry == "D_800000"


def test_cdwfi_with_two_args_uses_explicit_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_900000" / "instance" / "W_002"
    root.mkdir(parents=True)
    shell = _shell(tmp_path)
    shell.resolver = EntryPathResolver(
        path_info=type(
            "PI",
            (),
            {"getInstancePath": staticmethod(lambda dataSetId, wfInstanceId: str(tmp_path / "archive" / dataSetId / "instance" / wfInstanceId))},
        )()
    )

    shell.do_cdwfi("D_900000 W_002")

    import os

    assert os.getcwd() == str(root)
    assert shell.context.current_entry == "D_900000"


def test_cdwfi_without_entry_reports_usage_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)

    shell.do_cdwfi("W_001")

    output = capsys.readouterr()
    assert "Usage: cdwfi" in (output.out + output.err)


def test_ls_aliases_files_list(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("contents")
    shell = _shell(tmp_path)

    shell.do_ls("--type model")

    assert "D_800000_model_P1.cif.V1" in capsys.readouterr().out


def test_ff_aliases_files_find(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("contents")
    shell = _shell(tmp_path)

    shell.do_ff("--type model")

    assert "D_800000_model_P1.cif.V1" in capsys.readouterr().out


def test_prompt_shows_current_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    shell = _shell(tmp_path)

    assert str(tmp_path) in shell.prompt
