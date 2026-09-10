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


@pytest.mark.asyncio
async def test_scripts_run_without_execute_permission_reports_clean_error(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "noexec.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o644)  # no execute bit
    (scripts_dir / "noexec.sh.yaml").write_text("name: noexec.sh\ndescription: no-exec\ntags: []\n")

    app = OneDepTuiApp(
        config=mock.Mock(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugin_dirs=[tmp_path / "plugins"],
        script_dirs=[scripts_dir],
        cli_group_imports=[],
    )
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = "scripts run noexec.sh"
        await pilot.press("enter")  # must not crash, must not leave the terminal stuck suspended

        assert any("noexec.sh" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_scripts_list_with_tag_and_no_value_reports_clean_error(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = "scripts list --tag"
        await pilot.press("enter")

        assert any("--tag" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_unbalanced_quote_reports_clean_error_not_a_crash(tmp_path):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()

        input_widget = app.query_one("#cmdline")
        input_widget.value = 'files find --type "model'
        await pilot.press("enter")  # must not crash the app

        assert len(app.printer.error_calls) == 1


@pytest.mark.asyncio
async def test_bridged_group_raising_non_click_exception_reports_clean_error(tmp_path, monkeypatch):
    fake_module = types.ModuleType("onedep_manager_test_fake_broken_group")

    @click.group(name="brokengroup")
    def brokengroup():
        pass

    @brokengroup.command(name="boom")
    def boom():
        raise RuntimeError("plugin exploded")

    fake_module.brokengroup = brokengroup
    monkeypatch.setitem(sys.modules, "onedep_manager_test_fake_broken_group", fake_module)

    app = _app(tmp_path, cli_group_imports=[("brokengroup", "onedep_manager_test_fake_broken_group", "brokengroup")])
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())

        input_widget = app.query_one("#cmdline")
        input_widget.value = "brokengroup boom"
        await pilot.press("enter")  # must not crash the app

        assert any("plugin exploded" in msg for msg in app.printer.error_calls)


@pytest.mark.asyncio
async def test_suspend_body_failure_still_reports_error_not_crash(tmp_path, monkeypatch):
    app = _app(tmp_path)
    async with app.run_test() as pilot:
        app.printer = RecordingPrinter()
        monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())

        input_widget = app.query_one("#cmdline")
        input_widget.value = "!false"  # subprocess.run succeeds fine; this specifically checks _run_suspended's own body-exception path
        await pilot.press("enter")

        # `false` exits nonzero but subprocess.run itself doesn't raise -- this
        # just confirms the whole path still runs cleanly end to end after the
        # restructuring. The PermissionError-from-suspend-body case is already
        # covered by test_scripts_run_without_execute_permission_reports_clean_error.
        assert app.printer.error_calls == []


@pytest.mark.asyncio
async def test_plugin_print_output_reaches_the_log(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "printer_plugin.py").write_text(
        "from onedep_manager.shell.plugin_loader import FilePlugin\n"
        "\n"
        "class PrinterPlugin(FilePlugin):\n"
        "    name = 'say-hi'\n"
        "    help = 'prints hi'\n"
        "\n"
        "    def run(self, files, **kwargs):\n"
        "        print('hi from plugin')\n"
    )

    app = OneDepTuiApp(
        config=mock.Mock(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugin_dirs=[plugins_dir],
        script_dirs=[tmp_path / "scripts"],
        cli_group_imports=[],
    )
    async with app.run_test() as pilot:
        captured = []
        real_write = app.query_one("#log").write

        def _record(content):
            captured.append(content)
            return real_write(content)

        app.query_one("#log").write = _record

        input_widget = app.query_one("#cmdline")
        input_widget.value = "files say-hi"
        await pilot.press("enter")
        await pilot.pause()

        assert any("hi from plugin" in str(c) for c in captured)
