from pathlib import Path

import pytest

from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.plugins.copy import CopyPlugin
from onedep_manager.shell.resolver import EntryPathResolver


class FakePathInfo:
    def getDepositPath(self, dataSetId):
        return str(Path("/data/deposit") / dataSetId)


@pytest.fixture
def plugin():
    return CopyPlugin()


@pytest.fixture
def resolver():
    return EntryPathResolver(path_info=FakePathInfo())


def _make_files(src_dir, *names):
    src_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for name in names:
        p = src_dir / name
        p.write_text(name)
        files.append(p)
    return files


def test_copy_to_dest_creates_missing_directory_and_copies_files(tmp_path, plugin, resolver, capsys):
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")
    dest = tmp_path / "out"

    plugin.run(files, context=ShellContext(), resolver=resolver, dest=str(dest))

    assert (dest / "D_800000_model_P1.cif.V1").read_text() == "D_800000_model_P1.cif.V1"
    assert "copied" in capsys.readouterr().out


def test_copy_to_repo_resolves_current_entry_via_resolver(tmp_path, plugin, resolver, monkeypatch, capsys):
    deposit_root = tmp_path / "data" / "deposit" / "D_800000"
    monkeypatch.setattr(resolver, "resolve", lambda entry_id, repo: deposit_root)
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")
    context = ShellContext()
    context.set_entry("D_800000")

    plugin.run(files, context=context, resolver=resolver, repo="deposit")

    assert (deposit_root / "D_800000_model_P1.cif.V1").exists()


def test_copy_to_repo_without_current_entry_reports_error(tmp_path, plugin, resolver, capsys):
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")

    plugin.run(files, context=ShellContext(), resolver=resolver, repo="deposit")

    assert "no entry selected" in capsys.readouterr().out


def test_copy_with_unknown_repo_reports_clean_error(tmp_path, plugin, resolver, capsys):
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")
    context = ShellContext()
    context.set_entry("D_800000")

    plugin.run(files, context=context, resolver=resolver, repo="not-a-repo")

    assert "Unknown repository" in capsys.readouterr().out


def test_copy_with_both_dest_and_repo_reports_usage_error(tmp_path, plugin, resolver, capsys):
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")

    plugin.run(files, context=ShellContext(), resolver=resolver, dest=str(tmp_path / "out"), repo="deposit")

    assert "Usage: files copy" in capsys.readouterr().out


def test_copy_with_neither_dest_nor_repo_reports_usage_error(tmp_path, plugin, resolver, capsys):
    files = _make_files(tmp_path / "src", "D_800000_model_P1.cif.V1")

    plugin.run(files, context=ShellContext(), resolver=resolver)

    assert "Usage: files copy" in capsys.readouterr().out


def test_copy_with_no_files_selected_reports_message(plugin, resolver, capsys):
    plugin.run([], context=ShellContext(), resolver=resolver, dest="/tmp/out")

    assert "No files selected" in capsys.readouterr().out
