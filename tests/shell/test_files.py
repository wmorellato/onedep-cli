import hashlib
from io import StringIO
from pathlib import Path

import pytest

from onedep_manager.cli.common import RawPrinter
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.files import FilesCommands
from onedep_manager.shell.plugin_loader import FilePlugin
from onedep_manager.shell.resolver import EntryPathResolver


class FakePathInfo:
    def getArchivePath(self, dataSetId):
        return str(Path.cwd())  # overridden per-test via monkeypatch/tmp_path chdir


class RecordingPlugin(FilePlugin):
    name = "record"
    help = "Records the files it was called with"

    def __init__(self):
        self.calls = []

    def run(self, files, **kwargs):
        self.calls.append(list(files))


class _App(FilesCommands):
    def __init__(self, context, resolver, plugins, stream):
        self.context = context
        self.resolver = resolver
        self.plugins = plugins
        self.printer = RawPrinter(stream=stream)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("model contents")
    (tmp_path / "D_800000_sf_P1.cif.V1").write_text("sf contents")
    (tmp_path / "README.md").write_text("not a wwpdb file")

    stream = StringIO()
    plugin = RecordingPlugin()
    application = _App(
        context=ShellContext(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugins={"record": plugin},
        stream=stream,
    )
    application._stream = stream
    application._plugin = plugin
    return application


def test_find_lists_matches_without_selecting(app):
    app.dispatch(["find", "--type", "model"])

    output = app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" in output
    assert app.context.current_selection == []


def test_find_with_select_stores_selection(app):
    app.dispatch(["find", "--type", "model", "-s"])

    assert [p.name for p in app.context.current_selection] == ["D_800000_model_P1.cif.V1"]


def test_find_table_includes_md5_column(app):
    app.dispatch(["find", "--type", "model"])

    expected_md5 = hashlib.md5(b"model contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()


def test_list_shows_current_selection(app):
    app.context.set_selection([Path.cwd() / "D_800000_model_P1.cif.V1"])

    app.dispatch(["list"])

    assert "D_800000_model_P1.cif.V1" in app._stream.getvalue()


def test_list_ignores_filter_style_args_and_uses_selection(app):
    app.context.set_selection([Path.cwd() / "D_800000_sf_P1.cif.V1"])

    app.dispatch(["list"])

    assert "D_800000_sf_P1.cif.V1" in app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" not in app._stream.getvalue()


def test_hash_action_renders_selection_table(app):
    app.context.set_selection([Path.cwd() / "D_800000_model_P1.cif.V1"])

    app.dispatch(["hash"])

    expected_md5 = hashlib.md5(b"model contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()


def test_hash_action_accepts_one_shot_filters(app):
    app.dispatch(["hash", "--type", "sf"])

    expected_md5 = hashlib.md5(b"sf contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()
    # one-shot filters must not mutate the stored selection
    assert app.context.current_selection == []


def test_unknown_action_reports_error(app):
    app.dispatch(["bogus"])

    assert "Unknown files action" in app._stream.getvalue()


def test_dispatch_with_no_args_reports_usage(app):
    app.dispatch([])

    assert "Usage: files" in app._stream.getvalue()


def test_dispatch_to_plugin_passes_current_selection(app):
    selection = [Path.cwd() / "D_800000_model_P1.cif.V1"]
    app.context.set_selection(selection)

    app.dispatch(["record"])

    assert app._plugin.calls == [selection]


def test_invalid_flag_reports_error_without_crashing(app):
    # argparse's default parser calls sys.exit() on a bad flag, which would
    # kill the whole shell process on a user typo -- this must instead be
    # reported like any other files error.
    app.dispatch(["find", "--not-a-real-flag"])

    assert "files find" in app._stream.getvalue()
