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


class RaisingPlugin(FilePlugin):
    name = "explode"
    help = "Always raises"

    def run(self, files, **kwargs):
        raise RuntimeError("plugin boom")


class KwargsRecordingPlugin(FilePlugin):
    name = "kwrecord"
    help = "Records the kwargs it was called with"

    def __init__(self):
        self.last_kwargs = None

    def run(self, files, **kwargs):
        self.last_kwargs = kwargs


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
    kwargs_plugin = KwargsRecordingPlugin()
    application = _App(
        context=ShellContext(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugins={"record": plugin, "explode": RaisingPlugin(), "kwrecord": kwargs_plugin},
        stream=stream,
    )
    application._stream = stream
    application._plugin = plugin
    application._kwargs_plugin = kwargs_plugin
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


def test_find_with_current_entry_and_no_filters_lists_entry_archive_directory(app):
    app.context.set_entry("D_800000")

    app.dispatch(["find"])

    output = app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" in output
    assert "D_800000_sf_P1.cif.V1" in output


def test_find_with_repo_override_and_no_entry_falls_back_to_cwd(app):
    # No entry set, so --repo alone has nowhere to resolve an entry-scoped
    # directory to; this must fall through to the existing cwd-based
    # candidate lookup rather than silently returning nothing.
    app.dispatch(["find", "--repo", "deposit"])

    output = app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" in output


def test_dispatch_with_no_args_reports_usage(app):
    app.dispatch([])

    assert "Usage: files" in app._stream.getvalue()


def test_dispatch_to_plugin_passes_current_selection(app):
    selection = [Path.cwd() / "D_800000_model_P1.cif.V1"]
    app.context.set_selection(selection)

    app.dispatch(["record"])

    assert app._plugin.calls == [selection]


def test_plugin_exception_is_reported_and_does_not_propagate(app):
    app.dispatch(["explode"])

    assert "plugin boom" in app._stream.getvalue()


def test_plugin_receives_parsed_keyword_arguments(app):
    app.dispatch(["kwrecord", "--dest", "/tmp", "--verbose"])

    assert app._kwargs_plugin.last_kwargs == {"dest": "/tmp", "verbose": True}


def test_plugin_with_no_extra_args_gets_empty_kwargs(app):
    app.dispatch(["kwrecord"])

    assert app._kwargs_plugin.last_kwargs == {}


def test_dispatch_usage_message_lists_loaded_plugin_names(app):
    app.dispatch([])

    output = app._stream.getvalue()
    assert "record" in output
    assert "explode" in output
    assert "kwrecord" in output


def test_find_with_bad_version_reports_clean_error(app):
    app.dispatch(["find", "--type", "model", "--version", "abc"])

    assert "files find" in app._stream.getvalue()


def test_invalid_flag_reports_error_without_crashing(app):
    # argparse's default parser calls sys.exit() on a bad flag, which would
    # kill the whole shell process on a user typo -- this must instead be
    # reported like any other files error.
    app.dispatch(["find", "--not-a-real-flag"])

    assert "files find" in app._stream.getvalue()
