import importlib
import logging
import shlex
from pathlib import Path
from typing import List, Optional, Tuple

import cmd2
from rich.console import Console

from onedep_manager.cli.common import CLIContext, ConsolePrinter
from onedep_manager.config import Config
from onedep_manager.shell.bridging import bridge_click_group
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.files import FilesCommands
from onedep_manager.shell.plugin_loader import load_plugins
from onedep_manager.shell.resolver import EntryPathResolver
from onedep_manager.shell.scripts import ScriptNotFoundError, ScriptRegistry

logger = logging.getLogger(__name__)

DEFAULT_CLI_GROUP_IMPORTS: List[Tuple[str, str, str]] = [
    ("services", "onedep_manager.cli.services", "services_group"),
    ("tools", "onedep_manager.cli.tools", "tools_group"),
    ("packages", "onedep_manager.cli.packages", "packages_group"),
    ("instance", "onedep_manager.cli.instance", "instance_group"),
    ("config", "onedep_manager.cli.config", "config_group"),
    ("paths", "onedep_manager.cli.paths", "paths_group"),
]

_SHELL_PACKAGE_DIR = Path(__file__).parent
DEFAULT_PLUGIN_DIRS = [_SHELL_PACKAGE_DIR / "plugins", Path.home() / ".onedep" / "shell" / "plugins"]
DEFAULT_SCRIPT_DIRS = [_SHELL_PACKAGE_DIR / "scripts", Path.home() / ".onedep" / "shell" / "scripts"]

# Rich's Table truncates cells (e.g. long archive paths, full md5 hashes)
# to fit the console width, and falls back to a fixed 80-column width
# whenever stdout isn't a real terminal (piped/redirected output, or
# captured in tests). That default is too narrow for `files` output where
# the exact path/hash matters, so it's widened only in that non-interactive
# case -- a real terminal keeps its own auto-detected width untouched.
_NON_TERMINAL_CONSOLE_WIDTH = 200


def _build_console() -> Console:
    console = Console()
    if not console.is_terminal:
        console.width = _NON_TERMINAL_CONSOLE_WIDTH
    return console


class OneDepShell(FilesCommands, cmd2.Cmd):
    """Interactive shell launched by `onedep-manager shell`."""

    def __init__(
        self,
        config: Optional[Config] = None,
        site: Optional[str] = None,
        resolver: Optional[EntryPathResolver] = None,
        plugin_dirs: Optional[List[Path]] = None,
        script_dirs: Optional[List[Path]] = None,
        cli_group_imports: Optional[List[Tuple[str, str, str]]] = None,
    ):
        super().__init__(allow_cli_args=False)

        self.config = config or Config()
        self.context = ShellContext()
        self.resolver = resolver or EntryPathResolver(site=site)
        self.printer = ConsolePrinter(console=_build_console())
        self.plugins = load_plugins(plugin_dirs if plugin_dirs is not None else DEFAULT_PLUGIN_DIRS)
        self.scripts = ScriptRegistry(script_dirs if script_dirs is not None else DEFAULT_SCRIPT_DIRS)

        self._bridge_cli_groups(cli_group_imports if cli_group_imports is not None else DEFAULT_CLI_GROUP_IMPORTS)
        self._update_prompt()

    def _bridge_cli_groups(self, cli_group_imports: List[Tuple[str, str, str]]) -> None:
        ctx_obj = CLIContext(config=self.config)

        for name, module_path, attr in cli_group_imports:
            try:
                module = importlib.import_module(module_path)
                group = getattr(module, attr)
            except (ImportError, AttributeError) as exc:
                self.pwarning(f"Skipping '{name}' commands (missing dependency): {exc}")
                continue

            bridge_click_group(self, group, ctx_obj=ctx_obj)

    def _update_prompt(self) -> None:
        entry = self.context.current_entry or "-"
        count = len(self.context.current_selection)
        self.prompt = f"({entry}) [{count} files] onedep> "

    def do_entry(self, arg) -> None:
        """Set or show the current entry id: `entry D_1000001`"""
        entry_id = str(arg).strip()

        if not entry_id:
            self.poutput(self.context.current_entry or "No entry set")
            return

        self.context.set_entry(entry_id)

        try:
            archive_path = self.resolver.resolve(entry_id, "archive")
            if not archive_path.is_dir():
                self.pwarning(f"Entry '{entry_id}' resolved to '{archive_path}', which does not exist")
        except Exception as exc:
            self.pwarning(f"Could not resolve archive path for entry '{entry_id}': {exc}")

        self._update_prompt()

    def do_files(self, arg) -> None:
        """File navigation/query commands: find, list, hash, info, or a plugin name."""
        self.dispatch(shlex.split(str(arg)))
        self._update_prompt()

    def do_scripts(self, arg) -> None:
        """Run or list registered scripts: `scripts list [--tag T]` / `scripts run <name> [args...]`"""
        args = shlex.split(str(arg))

        if not args:
            self.printer.error("Usage: scripts <list|run> ...")
            return

        action, rest = args[0], args[1:]

        if action == "list":
            tag = None
            if "--tag" in rest:
                tag_index = rest.index("--tag")
                if tag_index + 1 >= len(rest):
                    self.printer.error("Usage: scripts list --tag <tag>")
                    return
                tag = rest[tag_index + 1]
            for meta in self.scripts.list(tag=tag):
                self.poutput(f"{meta.name}\t{', '.join(meta.tags)}\t{meta.description}")
            return

        if action == "run":
            if not rest:
                self.printer.error("Usage: scripts run <name> [args...]")
                return
            try:
                code = self.scripts.run(rest[0], rest[1:])
            except ScriptNotFoundError as exc:
                self.printer.error(str(exc))
                return
            except (OSError, PermissionError) as exc:
                self.printer.error(f"scripts run {rest[0]}: {exc}")
                return
            if code != 0:
                self.printer.error(f"Script exited with code {code}")
            return

        self.printer.error(f"Unknown scripts action '{action}'")
