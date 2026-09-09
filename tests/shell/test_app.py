import sys
import types
from unittest import mock

import click

from onedep_manager.shell.app import OneDepShell
from onedep_manager.shell.resolver import EntryPathResolver


class FakePathInfo:
    def getArchivePath(self, dataSetId):
        return "/data/archive/" + dataSetId


@click.group(name="fakegroup", help="A fake bridged group")
def fakegroup():
    pass


@fakegroup.command(name="ping")
def ping():
    click.echo("pong")


def _shell(tmp_path, cli_group_imports=None):
    return OneDepShell(
        config=mock.Mock(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugin_dirs=[tmp_path / "plugins"],
        script_dirs=[tmp_path / "scripts"],
        cli_group_imports=cli_group_imports or [],
    )


def test_shell_constructs_without_real_wwpdb_or_click_groups(tmp_path):
    shell = _shell(tmp_path)
    assert shell.context.current_entry is None


def test_entry_command_sets_context_and_prompt(tmp_path):
    shell = _shell(tmp_path)

    shell.do_entry("D_1000001")

    assert shell.context.current_entry == "D_1000001"
    assert "D_1000001" in shell.prompt


def test_entry_command_with_no_args_shows_current_entry(tmp_path, capsys):
    shell = _shell(tmp_path)
    shell.context.set_entry("D_1000001")

    shell.do_entry("")

    assert "D_1000001" in capsys.readouterr().out


def test_bridges_successfully_importable_group(tmp_path, monkeypatch, capsys):
    # Register a fake module directly in sys.modules rather than relying on
    # a real file's dotted import path -- that path's resolution depends on
    # how the test process itself was launched (python -m pytest vs. a bare
    # pytest/poetry entry point insert cwd onto sys.path differently), which
    # this test must not depend on.
    fake_module = types.ModuleType("onedep_manager_test_fake_ok_group")
    fake_module.fakegroup = fakegroup
    monkeypatch.setitem(sys.modules, "onedep_manager_test_fake_ok_group", fake_module)

    shell = _shell(
        tmp_path,
        cli_group_imports=[("fakegroup", "onedep_manager_test_fake_ok_group", "fakegroup")],
    )

    shell.onecmd_plus_hooks("fakegroup ping")

    assert "pong" in capsys.readouterr().out


def test_skips_group_whose_import_fails(tmp_path):
    shell = _shell(
        tmp_path,
        cli_group_imports=[("nope", "this.module.does.not.exist", "nope_group")],
    )

    assert not hasattr(shell, "do_nope")


def test_files_command_dispatches_through_files_commands_mixin(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("contents")

    shell = _shell(tmp_path)
    shell.do_files("find --type model")

    assert "D_800000_model_P1.cif.V1" in capsys.readouterr().out


def test_scripts_list_and_run(tmp_path, capfd):
    # capfd (not capsys): `scripts run` shells out via subprocess.run(), which
    # writes directly to the inherited OS file descriptor -- capsys only
    # intercepts the sys.stdout Python object and never sees a child
    # process's writes, so it would report "hi" as missing even though the
    # script ran and printed it. capfd captures at the fd level and sees
    # both the in-process poutput() calls below and the subprocess's output.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "hello.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    (scripts_dir / "hello.sh.yaml").write_text("name: hello.sh\ndescription: greets\ntags: [demo]\n")

    shell = _shell(tmp_path)

    shell.do_scripts("list --tag demo")
    assert "hello.sh" in capfd.readouterr().out

    shell.do_scripts("run hello.sh")
    assert "hi" in capfd.readouterr().out


def test_scripts_run_unregistered_reports_error(tmp_path, capsys):
    shell = _shell(tmp_path)

    shell.do_scripts("run does-not-exist")

    assert "not registered" in capsys.readouterr().out or "not registered" in capsys.readouterr().err
