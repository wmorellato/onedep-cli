import contextlib
import importlib
import io
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.text import Text
from textual.app import App, ComposeResult
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
                self._run_shell_command(stripped[1:])
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
            elif action == "help":
                self._do_help()
            elif action in ("quit", "exit"):
                self.exit()
                return
            elif action in self._bridged_groups:
                self._run_bridged_command(stripped, self._bridged_groups[action], rest)
            else:
                self.printer.error(f"Unknown command '{action}'")
        except Exception as exc:
            self.printer.error(f"Error running '{stripped}': {exc}")

        self._refresh_panels()

    def _write_captured_output(self, stdout_text: str, stderr_text: str) -> None:
        log = self.query_one("#log", RichLog)
        if stdout_text:
            log.write(Text.from_ansi(stdout_text))
        if stderr_text:
            log.write(Text.from_ansi(stderr_text, style="red"))

    def _run_shell_command(self, cmd: str) -> None:
        """Run `cmd` in a real subprocess and write its output into the log.

        Output is captured rather than handing the terminal over to the
        subprocess: the TUI is actively rendering its own screen, and a
        subprocess writing directly to the real terminal while that's
        happening would corrupt the display. The trade-off: a command that
        needs a real interactive terminal (an editor, an SSH session) will
        not work through this -- there's no TTY for it to talk to.
        """
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        self._write_captured_output(result.stdout, result.stderr)
        if result.returncode != 0:
            self.printer.error(f"'!{cmd}' exited with code {result.returncode}")

    def _run_bridged_command(self, label: str, group: click.Group, args: List[str]) -> None:
        """Run a bridged Click group, capturing its stdout/stderr into the log.

        Uses contextlib.redirect_stdout/stderr rather than a real terminal
        handoff, for the same reason as `_run_shell_command`. Whatever was
        captured before a failure is still written (the `finally`), so a
        command that partially printed something before raising doesn't
        lose that output.
        """
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                invoke_click_group(group, args, ctx_obj=self._ctx_obj)
        finally:
            self._write_captured_output(stdout_buf.getvalue(), stderr_buf.getvalue())

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
                result = self.scripts.run(rest[0], rest[1:])
            except ScriptNotFoundError as exc:
                self.printer.error(str(exc))
                return
            except (OSError, PermissionError) as exc:
                self.printer.error(f"scripts run {rest[0]}: {exc}")
                return
            self._write_captured_output(result.stdout, result.stderr)
            if result.returncode != 0:
                self.printer.error(f"Script exited with code {result.returncode}")
            return

        self.printer.error(f"Unknown scripts action '{action}'")

    def _do_help(self) -> None:
        rows = [
            ["entry [ID]", "Set or show the current entry"],
            ["files find|list|hash|info [args...]", "Find/list/hash/info on wwPDB files"],
            ["scripts list|run [args...]", "List or run a whitelisted script"],
            ["!<command>", "Run <command> and show its output here"],
            ["quit / exit", "Exit the shell (Ctrl+Q also works)"],
            ["help", "Show this help"],
        ]

        if self.plugins:
            rows.append(["files <plugin> [args...]", "Loaded plugins: " + ", ".join(sorted(self.plugins))])

        if self._bridged_groups:
            rows.append(["<bridged command>", "Available: " + ", ".join(sorted(self._bridged_groups))])

        self.printer.table(["Command", "Description"], rows)
