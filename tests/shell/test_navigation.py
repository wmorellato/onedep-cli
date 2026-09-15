from io import StringIO
from unittest import mock

import pytest

from onedep_manager.cli.common import RawPrinter
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.navigation import CD_MNEMONICS, NavigationCommands
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


class _App(NavigationCommands):
    def __init__(self, config, resolver, stream):
        self.context = ShellContext()
        self.resolver = resolver
        self.config = config
        self.printer = RawPrinter(stream=stream)


@pytest.fixture
def resolver():
    return EntryPathResolver(path_info=FakePathInfo())


def _app(resolver, config=None):
    stream = StringIO()
    application = _App(config=config or mock.Mock(), resolver=resolver, stream=stream)
    application._stream = stream
    return application


def test_cd_with_explicit_identifier_chdirs_and_syncs_context(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "archive" / "D_800000"
    root.mkdir(parents=True)
    app = _app(resolver)
    app.resolver = EntryPathResolver(path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(root))})())

    app.do_cd(["archive", "D_800000"])

    import os

    assert os.getcwd() == str(root)
    assert app.context.current_entry == "D_800000"


def test_cd_falls_back_to_current_entry_when_identifier_omitted(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_800000"
    root.mkdir(parents=True)
    app = _app(resolver)
    app.resolver = EntryPathResolver(path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(root))})())
    app.context.set_entry("D_800000")

    app.do_cd(["archive"])

    import os

    assert os.getcwd() == str(root)


def test_cd_without_identifier_or_current_entry_reports_usage_error(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    app = _app(resolver)

    app.do_cd(["archive"])

    assert "Usage: cd archive" in app._stream.getvalue()


def test_cd_unknown_repo_reports_clean_error(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    app = _app(resolver)

    app.do_cd(["not-a-repo", "D_800000"])

    assert "Unknown repository" in app._stream.getvalue()


def test_cd_missing_directory_reports_error_and_does_not_chdir(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    app = _app(resolver)
    app.resolver = EntryPathResolver(
        path_info=type("PI", (), {"getArchivePath": staticmethod(lambda dataSetId: str(tmp_path / "missing"))})()
    )

    app.do_cd(["archive", "D_800000"])

    import os

    assert os.getcwd() == str(tmp_path)
    assert "directory not found" in app._stream.getvalue()


def test_cdd_mnemonic_resolves_deposit_repo(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "deposit" / "D_800000"
    root.mkdir(parents=True)
    app = _app(resolver)
    app.resolver = EntryPathResolver(path_info=type("PI", (), {"getDepositPath": staticmethod(lambda dataSetId: str(root))})())

    app.do_cd_mnemonic("cdd", ["D_800000"])

    import os

    assert os.getcwd() == str(root)
    assert app.context.current_entry == "D_800000"


def test_mnemonic_with_too_many_args_reports_usage_error(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    app = _app(resolver)

    app.do_cd_mnemonic("cdd", ["D_800000", "extra"])

    assert "Usage: cdd" in app._stream.getvalue()


def test_all_mnemonics_are_wired_to_a_known_repo(resolver):
    app = _app(resolver)
    for action, repo in CD_MNEMONICS.items():
        assert repo in set(app.resolver.known_repos) | {"session"}


def test_cds_uses_config_session_path_not_resolver(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    sessions_root = tmp_path / "sessions"
    (sessions_root / "abc123").mkdir(parents=True)
    config = mock.Mock()
    config.from_site.return_value = str(sessions_root)
    app = _app(resolver, config=config)

    app.do_cd_mnemonic("cds", ["abc123"])

    import os

    assert os.getcwd() == str(sessions_root / "abc123")
    config.from_site.assert_called_with("SITE_WEB_APPS_SESSIONS_PATH")


def test_cdwfi_with_one_arg_uses_current_entry(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_800000" / "instance" / "W_001"
    root.mkdir(parents=True)
    app = _app(resolver)
    app.resolver = EntryPathResolver(
        path_info=type(
            "PI",
            (),
            {"getInstancePath": staticmethod(lambda dataSetId, wfInstanceId: str(tmp_path / "archive" / dataSetId / "instance" / wfInstanceId))},
        )()
    )
    app.context.set_entry("D_800000")

    app.do_cdwfi(["W_001"])

    import os

    assert os.getcwd() == str(root)
    assert app.context.current_entry == "D_800000"


def test_cdwfi_with_two_args_uses_explicit_entry(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "archive" / "D_900000" / "instance" / "W_002"
    root.mkdir(parents=True)
    app = _app(resolver)
    app.resolver = EntryPathResolver(
        path_info=type(
            "PI",
            (),
            {"getInstancePath": staticmethod(lambda dataSetId, wfInstanceId: str(tmp_path / "archive" / dataSetId / "instance" / wfInstanceId))},
        )()
    )

    app.do_cdwfi(["D_900000", "W_002"])

    import os

    assert os.getcwd() == str(root)
    assert app.context.current_entry == "D_900000"


def test_cdwfi_without_entry_reports_usage_error(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    app = _app(resolver)

    app.do_cdwfi(["W_001"])

    assert "Usage: cdwfi" in app._stream.getvalue()
