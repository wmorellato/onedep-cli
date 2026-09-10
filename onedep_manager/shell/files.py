import argparse
import hashlib
import stat as stat_module
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from onedep_manager.cli.common import Printer
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.file_filters import FileAttributes, filter_files, parse_wwpdb_filename
from onedep_manager.shell.plugin_loader import FilePlugin
from onedep_manager.shell.resolver import EntryPathResolver, UnknownRepositoryError


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _owner_name(uid: int) -> str:
    try:
        import pwd

        return pwd.getpwuid(uid).pw_name
    except Exception:
        return str(uid)


def _render_table(printer: Printer, attrs: List[FileAttributes]) -> None:
    header = ["permissions", "owner", "size", "mtime", "md5", "path"]
    rows = []

    for a in attrs:
        st = a.path.stat()
        rows.append(
            [
                stat_module.filemode(st.st_mode),
                _owner_name(st.st_uid),
                str(st.st_size),
                datetime.fromtimestamp(st.st_mtime).isoformat(sep=" ", timespec="seconds"),
                _md5(a.path),
                str(a.path),
            ]
        )

    printer.table(header, rows)


class _ArgumentParserError(Exception):
    """Raised instead of exiting the process on a bad `files` flag."""


class _NonExitingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise _ArgumentParserError(message)


def _parse_plugin_kwargs(rest: List[str]) -> Dict[str, object]:
    """Parse a plugin's trailing `--key value` / `--flag` tokens into a dict.

    Walks `rest`; for each token starting with `--`, if the next token is
    missing or also starts with `--`, it's treated as a boolean flag
    (`True`); otherwise the next token is consumed as its string value.
    The leading `--` is stripped and internal `-` becomes `_` for the key
    (e.g. `--dest /tmp` -> {"dest": "/tmp"}, `--verbose` -> {"verbose": True}).
    """
    kwargs: Dict[str, object] = {}
    i = 0
    while i < len(rest):
        token = rest[i]
        if token.startswith("--"):
            key = token[2:].replace("-", "_")
            if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                kwargs[key] = rest[i + 1]
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            i += 1
    return kwargs


def _shared_parser(allow_select: bool) -> argparse.ArgumentParser:
    parser = _NonExitingArgumentParser(add_help=False)
    parser.add_argument("--type", dest="type_", help="Comma-separated content types (e.g. model,model-upload)")
    parser.add_argument("--milestone", help="Content-type milestone suffix (e.g. upload)")
    parser.add_argument("--version", help="Exact version number, or 'latest'")
    parser.add_argument("--entry", help="Deposition id; defaults to the current entry context")
    parser.add_argument("--repo", default="archive", help="Repository to search when an entry is set (default: archive)")
    if allow_select:
        parser.add_argument("-s", "--select", action="store_true", help="Store matches as the current selection")
    return parser


class FilesCommands:
    """File find/list/action commands.

    Composed into onedep_manager.shell.tui.app.OneDepTuiApp. Requires the host
    object to provide `context`, `resolver`, `plugins`, and `printer`
    attributes (see the class-level type hints below).
    """

    context: ShellContext
    resolver: EntryPathResolver
    plugins: Dict[str, FilePlugin]
    printer: Printer

    def _candidate_files(self, entry: Optional[str], repo: str) -> List[Path]:
        entry_id = entry or self.context.current_entry

        if entry_id:
            directory = self.resolver.resolve(entry_id, repo)
        else:
            directory = Path.cwd()

        if not directory.is_dir():
            return []

        return sorted(p for p in directory.iterdir() if p.is_file())

    def _resolve_target(self, args: List[str], allow_select: bool) -> List[FileAttributes]:
        parser = _shared_parser(allow_select)
        parsed = parser.parse_args(args)

        has_filters = any(
            [
                parsed.type_,
                parsed.milestone,
                parsed.version,
                parsed.entry,
                self.context.current_entry,
                parsed.repo != parser.get_default("repo"),
            ]
        )

        if has_filters:
            types = parsed.type_.split(",") if parsed.type_ else None
            files = self._candidate_files(parsed.entry, parsed.repo)
            try:
                matched = filter_files(files, types=types, milestone=parsed.milestone, version=parsed.version)
            except ValueError as exc:
                raise _ArgumentParserError(f"invalid --version value: {exc}") from exc
        else:
            matched = [a for a in (parse_wwpdb_filename(p) for p in self.context.current_selection) if a is not None]

        if allow_select and getattr(parsed, "select", False):
            self.context.set_selection([a.path for a in matched])

        return matched

    def files_find(self, args: List[str]) -> None:
        _render_table(self.printer, self._resolve_target(args, allow_select=True))

    def files_list(self, args: List[str]) -> None:
        _render_table(self.printer, self._resolve_target(args, allow_select=False))

    def files_hash(self, args: List[str]) -> None:
        _render_table(self.printer, self._resolve_target(args, allow_select=False))

    def files_info(self, args: List[str]) -> None:
        _render_table(self.printer, self._resolve_target(args, allow_select=False))

    def dispatch(self, argv: List[str]) -> None:
        if not argv:
            usage = "Usage: files <find|list|hash|info|plugin-name> [args...]"
            if self.plugins:
                usage += f" (loaded plugins: {', '.join(sorted(self.plugins))})"
            self.printer.error(usage)
            return

        action, rest = argv[0], argv[1:]

        builtin = {
            "find": self.files_find,
            "list": self.files_list,
            "hash": self.files_hash,
            "info": self.files_info,
        }.get(action)

        if builtin is not None:
            try:
                builtin(rest)
            except UnknownRepositoryError as exc:
                self.printer.error(str(exc))
            except _ArgumentParserError as exc:
                self.printer.error(f"files {action}: {exc}")
            return

        plugin = self.plugins.get(action)
        if plugin is None:
            self.printer.error(f"Unknown files action '{action}'")
            return

        kwargs = _parse_plugin_kwargs(rest)
        try:
            plugin.run(self.context.current_selection, **kwargs)
        except Exception as exc:
            self.printer.error(f"files {action}: {exc}")
