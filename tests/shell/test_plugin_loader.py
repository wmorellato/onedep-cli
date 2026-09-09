import logging
from pathlib import Path

from onedep_manager.shell.plugin_loader import FilePlugin, load_plugins

GOOD_PLUGIN = '''
from onedep_manager.shell.plugin_loader import FilePlugin


class DemoPlugin(FilePlugin):
    name = "demo"
    help = "A demo plugin"

    def run(self, files, **kwargs):
        pass
'''

BROKEN_PLUGIN = '''
raise RuntimeError("boom: this plugin is broken")
'''

BROKEN_INSTANTIATION_PLUGIN = '''
from onedep_manager.shell.plugin_loader import FilePlugin


class BadInitPlugin(FilePlugin):
    name = "bad-init"
    help = "Raises on construction"

    def __init__(self):
        raise ValueError("cannot construct me")

    def run(self, files, **kwargs):
        pass
'''


def test_loads_valid_plugin(tmp_path):
    (tmp_path / "good.py").write_text(GOOD_PLUGIN)

    plugins = load_plugins([tmp_path])

    assert "demo" in plugins
    assert isinstance(plugins["demo"], FilePlugin)
    assert plugins["demo"].help == "A demo plugin"


def test_skips_plugin_that_raises_on_import(tmp_path, caplog):
    (tmp_path / "good.py").write_text(GOOD_PLUGIN)
    (tmp_path / "broken.py").write_text(BROKEN_PLUGIN)

    with caplog.at_level(logging.WARNING):
        plugins = load_plugins([tmp_path])

    assert "demo" in plugins
    assert any("broken.py" in record.message or "broken.py" in str(record.args) for record in caplog.records) or any(
        "broken.py" in caplog.text for _ in [None]
    )


def test_skips_plugin_that_raises_on_instantiation(tmp_path, caplog):
    (tmp_path / "bad_init.py").write_text(BROKEN_INSTANTIATION_PLUGIN)

    with caplog.at_level(logging.WARNING):
        plugins = load_plugins([tmp_path])

    assert "bad-init" not in plugins
    assert "bad_init.py" in caplog.text


def test_missing_directory_is_skipped_silently(tmp_path):
    missing = tmp_path / "does-not-exist"

    plugins = load_plugins([missing])

    assert plugins == {}


def test_files_starting_with_underscore_are_ignored(tmp_path):
    (tmp_path / "_helpers.py").write_text(GOOD_PLUGIN.replace("DemoPlugin", "HelperNotAPlugin").replace('"demo"', '"should-not-load"'))

    plugins = load_plugins([tmp_path])

    assert plugins == {}


def test_multiple_directories_merge_with_later_dirs_winning(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()

    (builtin_dir / "demo.py").write_text(GOOD_PLUGIN)
    (user_dir / "demo_override.py").write_text(GOOD_PLUGIN.replace("A demo plugin", "User override"))

    plugins = load_plugins([builtin_dir, user_dir])

    assert plugins["demo"].help == "User override"
