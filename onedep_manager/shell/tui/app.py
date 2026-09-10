import importlib
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import click
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.containers import Vertical
from textual.widgets import RichLog

from onedep_manager.cli.common import CLIContext
from onedep_manager.config import Config
from onedep_manager.shell.bridging import invoke_click_group
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.files import FilesCommands
from onedep_manager.shell.plugin_loader import load_plugins
from onedep_manager.shell.resolver import EntryPathResolver
from onedep_manager.shell.scripts import ScriptNotFoundError, ScriptRegistry
from onedep_manager.shell.tui.input import HistoryInput
from onedep_manager.shell.tui.panels import EntrySelectionPanel, Panel
from onedep_manager.shell.tui.printer import TextualPrinter

DEFAULT_CLI_GROUP_IMPORTS: List[Tuple[str, str, str]] = [
    ("services", "onedep_manager.cli.services", "services_group"),
    ("tools", "onedep_manager.cli.tools", "tools_group"),
    ("packages", "onedep_manager.cli.packages", "packages_group"),
    ("instance", "onedep_manager.cli.instance", "instance_group"),
    ("config", "onedep_manager.cli.config", "config_group"),
    ("paths", "onedep_manager.cli.paths", "paths_group"),
]

_SHELL_PACKAGE_DIR = Path(__file__).parent.parent
DEFAULT_PLUGIN_DIRS = [_SHELL_PACKAGE_DIR / "plugins", Path.home() / ".onedep" / "shell" / "plugins"]
DEFAULT_SCRIPT_DIRS = [_SHELL_PACKAGE_DIR / "scripts", Path.home() / ".onedep" / "shell" / "scripts"]


def _default_pause_for_return() -> None:
    """Block for a keypress before the TUI resumes from a suspended command.

    Without this, a fast command's output (e.g. `ls`) can be erased by the
    TUI's redraw before there's any chance to read it -- the suspend/resume
    round-trip can be faster than a human can perceive. `input()` here reads
    from the real terminal, which is what `self.suspend()` hands control
    back to.
    """
    try:
        input("\nPress Enter to return to onedep-manager shell...")
    except EOFError:
        pass


class OneDepTuiApp(FilesCommands, App):
    """Interactive TUI shell launched by `onedep-manager shell`."""

    CSS = """
    #panels {
        dock: top;
        height: auto;
        border: round $accent;
        background: $boost;
        padding: 1 2;
    }

    RichLog {
        height: 1fr;
    }

    HistoryInput {
        dock: bottom;
    }
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        site: Optional[str] = None,
        resolver: Optional[EntryPathResolver] = None,
        plugin_dirs: Optional[List[Path]] = None,
        script_dirs: Optional[List[Path]] = None,
        cli_group_imports: Optional[List[Tuple[str, str, str]]] = None,
        pause_for_return: Optional[Callable[[], None]] = None,
    ):
        super().__init__()

        self.config = config or Config()
        self.context = ShellContext()
        self.resolver = resolver or EntryPathResolver(site=site)
        self.plugins = load_plugins(plugin_dirs if plugin_dirs is not None else DEFAULT_PLUGIN_DIRS)
        self.scripts = ScriptRegistry(script_dirs if script_dirs is not None else DEFAULT_SCRIPT_DIRS)
        self._cli_group_imports = cli_group_imports if cli_group_imports is not None else DEFAULT_CLI_GROUP_IMPORTS
        self._bridged_groups: Dict[str, click.Group] = {}
        self._ctx_obj = CLIContext(config=self.config)
        self._pause_for_return = pause_for_return or _default_pause_for_return
        self.printer = None  # set in on_mount, once the RichLog exists

    def compose(self) -> ComposeResult:
        with Vertical(id="panels"):
            yield EntrySelectionPanel(id="entry-panel")
        yield RichLog(id="log", markup=False, wrap=True)
        yield HistoryInput(id="cmdline", placeholder="command...")

    def on_mount(self) -> None:
        self.printer = TextualPrinter(self.query_one("#log", RichLog))
        self.begin_capture_print(self)
        self._resolve_cli_groups()
        self._refresh_panels()
        self.query_one("#cmdline", HistoryInput).focus()

    def on_print(self, event) -> None:
        self.query_one("#log", RichLog).write(event.text)

    def _resolve_cli_groups(self) -> None:
        for name, module_path, attr in self._cli_group_imports:
            try:
                module = importlib.import_module(module_path)
                group = getattr(module, attr)
            except (ImportError, AttributeError) as exc:
                self.printer.error(f"Skipping '{name}' commands (missing dependency): {exc}")
                continue
            self._bridged_groups[name] = group

    def _refresh_panels(self) -> None:
        for panel in self.query(Panel):
            panel.refresh_from_context(self.context)

    def on_input_submitted(self, event: HistoryInput.Submitted) -> None:
        input_widget = event.input
        line = event.value
        input_widget.add_to_history(line)
        input_widget.value = ""

        stripped = line.strip()
        if not stripped:
            return

        try:
            if stripped.startswith("!"):
                self._run_suspended(f"!{stripped[1:]}", lambda: subprocess.run(stripped[1:], shell=True))
                self._refresh_panels()
                return

            args = shlex.split(stripped)
            action, rest = args[0], args[1:]

            if action == "entry":
                self._do_entry(rest)
            elif action == "files":
                self.dispatch(rest)
            elif action == "scripts":
                self._do_scripts(rest)
            elif action in ("quit", "exit"):
                self.exit()
                return
            elif action in self._bridged_groups:
                group = self._bridged_groups[action]
                self._run_suspended(stripped, lambda: invoke_click_group(group, rest, ctx_obj=self._ctx_obj))
            else:
                self.printer.error(f"Unknown command '{action}'")
        except Exception as exc:
            self.printer.error(f"Error running '{stripped}': {exc}")

        self._refresh_panels()

    def _run_suspended(self, label: str, action) -> None:
        """Run `action` with the TUI suspended, reporting any failure cleanly.

        Catches everything `action` can raise *inside* the `with
        self.suspend():` block and never lets it escape that block --
        Textual's suspend() has no try/finally around resuming the
        terminal, so an exception escaping it leaves the terminal stuck
        in suspended state (verified during the final review: a script
        without its execute bit left the terminal permanently suspended
        before this fix). Also pauses for a keypress before resuming, so a
        fast command's output isn't erased by the redraw before it can be
        read.
        """
        failure = None
        try:
            with self.suspend():
                try:
                    action()
                except BaseException as exc:  # noqa: BLE001 -- must never escape suspend()
                    failure = exc
                self._pause_for_return()
        except SuspendNotSupported:
            self.printer.error(f"Cannot run '{label}' here: suspending the TUI isn't supported in this environment")
            return

        if failure is not None:
            self.printer.error(f"'{label}' failed: {failure}")

    def _do_entry(self, args: List[str]) -> None:
        if not args:
            self.printer.info(self.context.current_entry or "No entry set")
            return

        entry_id = args[0]
        self.context.set_entry(entry_id)

        try:
            archive_path = self.resolver.resolve(entry_id, "archive")
            if not archive_path.is_dir():
                self.printer.error(f"Entry '{entry_id}' resolved to '{archive_path}', which does not exist")
        except Exception as exc:
            self.printer.error(f"Could not resolve archive path for entry '{entry_id}': {exc}")

    def _do_scripts(self, args: List[str]) -> None:
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
                self.printer.info(f"{meta.name}\t{', '.join(meta.tags)}\t{meta.description}")
            return

        if action == "run":
            if not rest:
                self.printer.error("Usage: scripts run <name> [args...]")
                return
            try:
                code = self._run_script(rest[0], rest[1:])
            except ScriptNotFoundError as exc:
                self.printer.error(str(exc))
                return
            except (OSError, PermissionError) as exc:
                self.printer.error(f"scripts run {rest[0]}: {exc}")
                return
            if code is not None and code != 0:
                self.printer.error(f"Script exited with code {code}")
            return

        self.printer.error(f"Unknown scripts action '{action}'")

    def _run_script(self, name: str, args: List[str]) -> Optional[int]:
        """Run a registered script with the TUI suspended.

        Returns the script's exit code, or None if it couldn't run at all
        (suspend unsupported) -- distinct from a successful run that
        happens to exit 0. Any exception `self.scripts.run` raises
        (ScriptNotFoundError, OSError/PermissionError, ...) is re-raised
        here *after* the suspend block has safely exited, so it still
        reaches _do_scripts's existing except clauses -- but the terminal
        is never left stuck suspended getting there. Also pauses for a
        keypress before resuming, so the script's output isn't erased by
        the redraw before it can be read.
        """
        result = {}
        failure = None

        try:
            with self.suspend():
                try:
                    result["code"] = self.scripts.run(name, args)
                except BaseException as exc:  # noqa: BLE001 -- must never escape suspend()
                    failure = exc
                self._pause_for_return()
        except SuspendNotSupported:
            self.printer.error(f"Cannot run script '{name}' here: suspending the TUI isn't supported in this environment")
            return None

        if failure is not None:
            raise failure

        return result.get("code")
