from pathlib import Path

from onedep_manager.shell.context import ShellContext


def test_defaults():
    ctx = ShellContext()
    assert ctx.current_entry is None
    assert ctx.current_selection == []


def test_set_entry_clears_selection():
    ctx = ShellContext()
    ctx.set_selection([Path("/tmp/a"), Path("/tmp/b")])

    ctx.set_entry("D_1000001")

    assert ctx.current_entry == "D_1000001"
    assert ctx.current_selection == []


def test_set_selection():
    ctx = ShellContext()
    files = [Path("/tmp/a"), Path("/tmp/b")]

    ctx.set_selection(files)

    assert ctx.current_selection == files
    # set_selection must copy, not alias, the input list
    files.append(Path("/tmp/c"))
    assert ctx.current_selection == [Path("/tmp/a"), Path("/tmp/b")]


def test_clear_selection():
    ctx = ShellContext()
    ctx.set_selection([Path("/tmp/a")])

    ctx.clear_selection()

    assert ctx.current_selection == []
