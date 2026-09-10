import contextlib
import sys
import types
from unittest import mock

import click
import pytest

from onedep_manager.shell.resolver import EntryPathResolver
from onedep_manager.shell.tui.app import OneDepTuiApp
from onedep_manager.shell.tui.panels import EntrySelectionPanel


class FakePathInfo:
    def getArchivePath(self, dataSetId):
        return "/data/archive/" + dataSetId


class RecordingPrinter:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []
        self.table_calls = []
        self.json_calls = []

    def json(self, data):
        self.json_calls.append(data)

    def table(self, header, data):
        self.table_calls.append((header, data))

    def info(self, message):
        self.info_calls.append(message)

    def error(self, message):
        self.error_calls.append(message)


def _app(tmp_path, cli_group_imports=None):
    return OneDepTuiApp(
        config=mock.Mock(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugin_dirs=[tmp_path / "plugins"],
        script_dirs=[tmp_path / "scripts"],
        cli_group_imports=cli_group_imports or [],
    )


@pytest.mark.asyncio
async def test_app_constructs_and_mounts_without_real_wwpdb_or_click_groups(tmp_path):
    app = _app(tmp_path)
    async with app.run_test():
        assert app.context.current_entry is None
        assert app.query_one(EntrySelectionPanel) is not None


@pytest.mark.asyncio
async def test_entry_sets_context_and_refreshes_panel(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        input_widget = app.query_one("#cmdline")
        input_widget.value = "entry D_1000001"
        await pilot.press("enter")

        assert app.context.current_entry == "D_1000001"


@pytest.mark.asyncio
async def test_entry_with_no_args_reports_current_entry(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        app.context.set_entry("D_1000001")

        input_widget = app.query_one("#cmdline")
        input_widget.value = "entry"
        await pilot.press("enter")

        assert "D_1000001" in app.printer.info_calls


@pytest.mark.asyncio
async def test_entry_warns_when_resolved_path_does_not_exist(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = "entry D_9999999"
        await pilot.press("enter")

        assert app.context.current_entry == "D_9999999"
        assert any("D_9999999" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_files_command_dispatches_through_files_commands_mixin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("contents")

    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = "files find --type model"
        await pilot.press("enter")

        assert len(app.printer.table_calls) == 1
        header, rows = app.printer.table_calls[0]
        assert any("D_800000_model_P1.cif.V1" in row[-1] for row in rows)


@pytest.mark.asyncio
async def test_scripts_list_and_run(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "hello.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    (scripts_dir / "hello.sh.yaml").write_text("name: hello.sh\ndescription: greets\ntags: [demo]\n")

    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())

        input_widget = app.query_one("#cmdline")
        input_widget.value = "scripts list --tag demo"
        await pilot.press("enter")
        assert any("hello.sh" in msg for msg in app.printer.info_calls)

        input_widget.value = "scripts run hello.sh"
        await pilot.press("enter")
        assert app.printer.error_calls == []


@pytest.mark.asyncio
async def test_scripts_run_unregistered_reports_error(tmp_path, monkeypatch):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())

        input_widget = app.query_one("#cmdline")
        input_widget.value = "scripts run does-not-exist"
        await pilot.press("enter")

        assert any("not registered" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_bridged_group_runs_via_suspend(tmp_path, monkeypatch):
    fake_module = types.ModuleType("onedep_manager_test_fake_ok_group")

    @click.group(name="fakegroup")
    def fakegroup():
        pass

    @fakegroup.command(name="ping")
    def ping():
        click.echo("pong")

    fake_module.fakegroup = fakegroup
    monkeypatch.setitem(sys.modules, "onedep_manager_test_fake_ok_group", fake_module)

    app = _app(tmp_path, cli_group_imports=[("fakegroup", "onedep_manager_test_fake_ok_group", "fakegroup")])
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())

        input_widget = app.query_one("#cmdline")
        input_widget.value = "fakegroup ping"
        await pilot.press("enter")

        # invoke_click_group's own output goes to real stdout (that's the
        # point of suspend()), so there's nothing to assert on app.printer
        # for the command's own output -- just confirm dispatch didn't
        # error and didn't crash the app.
        assert app.printer.error_calls == []


@pytest.mark.asyncio
async def test_skips_group_whose_import_fails(tmp_path):
    app = _app(tmp_path, cli_group_imports=[("nope", "this.module.does.not.exist", "nope_group")])
    async with app.run_test():
        assert "nope" not in app._bridged_groups


@pytest.mark.asyncio
async def test_unknown_command_reports_error(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = "bogus"
        await pilot.press("enter")

        assert any("bogus" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_shell_delegation_runs_via_suspend(tmp_path, monkeypatch):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())
        calls = []
        monkeypatch.setattr("onedep_manager.shell.tui.app.subprocess.run", lambda cmd, shell: calls.append(cmd))

        input_widget = app.query_one("#cmdline")
        input_widget.value = "!echo hi"
        await pilot.press("enter")

        assert calls == ["echo hi"]


@pytest.mark.asyncio
async def test_suspend_not_supported_reports_clean_error(tmp_path, monkeypatch):
    from textual.app import SuspendNotSupported

    def _raise():
        raise SuspendNotSupported("nope")

    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", _raise)

        input_widget = app.query_one("#cmdline")
        input_widget.value = "!echo hi"
        await pilot.press("enter")  # must not raise

        assert any("echo hi" in msg or "suspend" in msg.lower() for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_quit_exits_the_app(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline")
        input_widget.value = "quit"
        await pilot.press("enter")

        assert not app.is_running
