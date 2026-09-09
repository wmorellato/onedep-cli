# Embedded Shell (`onedep-manager shell`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `onedep-manager shell`, a `cmd2`-based interactive shell that bridges in the existing Click command tree, adds stateful entry navigation, wwPDB-aware file find/select/act commands, drop-in file-action plugins, and a location-whitelisted script registry.

**Architecture:** A new `onedep_manager/shell/` package holds all shell logic as small, independently testable, dependency-injectable units (context, path resolver, file filters, plugin loader, script registry, file commands, Click-bridging, and the `cmd2.Cmd` app that wires them together). A thin `onedep_manager/cli/shell.py` Click command (following the existing `cli/*.py` pattern) instantiates and runs it.

**Tech Stack:** `cmd2` (new dependency), existing `click`, `rich` (via `onedep_manager/cli/common.py`'s `Printer`), `pyyaml`, stdlib `argparse`/`importlib`/`subprocess`/`hashlib`.

**Spec:** `docs/superpowers/specs/2026-09-09-embedded-shell-design.md`

## Global Constraints

- Bump `pyproject.toml`'s `python` floor from `^3.8` to `^3.9` and add `cmd2 = "^2.7"` — verified: cmd2 2.7.0 needs Python >=3.9 and only `rich-argparse>=1.7.1` (which needs `rich>=11.0.0`), so the existing `rich = "^13.0"` pin does **not** need to change.
- New shell logic lives under `onedep_manager/shell/`; the Click entry point is a thin wrapper in `onedep_manager/cli/shell.py`, matching this repo's existing split between `cli/*.py` (thin Click wrappers, see `onedep_manager/cli/paths.py`) and top-level implementation packages (see `onedep_manager/instance/`).
- Every new module must be importable, and every new unit test must be runnable, **without** `wwpdb.io`, `paramiko`, or `gitpython` installed. This dev sandbox only has `click`, `rich`, `pyyaml`, `pytest`, and `wwpdb.utils.config` available — `wwpdb.io`/`paramiko`/`gitpython` are missing, which already breaks collection of `tests/test_packages.py`, `tests/cli/test_packages.py`, `tests/cli/test_services.py`, and `tests/services/test_dispatcher.py` today (pre-existing, unrelated to this feature — do not try to fix it). Any real wwPDB/network/subprocess dependency (`PathInfo`, the real `services`/`packages`/`paths` Click groups) must be constructor-injectable so tests can substitute a fake.
- Reuse `onedep_manager/cli/common.py`'s `Printer`/`ConsolePrinter`/`RawPrinter` for all shell output — do not add a second output abstraction.
- Run only the test file(s) each task adds/touches (e.g. `pytest tests/shell/test_context.py -v`), not the whole suite — the whole suite has the pre-existing collection errors described above.
- Every new/modified `.py` file must stay under `onedep_manager/ruff`'s existing line-length (200) and lint rules (`E`, `F`, `B`); run `ruff check` on changed files before each commit if `ruff` is available in the environment.

---

## File Structure

```
pyproject.toml                              # modify: python floor, cmd2 dependency
onedep_manager/shell/__init__.py            # new (empty)
onedep_manager/shell/context.py             # new: ShellContext
onedep_manager/shell/resolver.py            # new: EntryPathResolver
onedep_manager/shell/file_filters.py        # new: wwPDB filename parsing/filtering
onedep_manager/shell/plugin_loader.py       # new: FilePlugin base class + loader
onedep_manager/shell/scripts.py             # new: ScriptRegistry
onedep_manager/shell/bridging.py            # new: bridge_click_group()
onedep_manager/shell/files.py               # new: FilesCommands mixin
onedep_manager/shell/app.py                 # new: OneDepShell(cmd2.Cmd)
onedep_manager/shell/plugins/               # new (empty dir, built-in plugins go here later)
onedep_manager/shell/scripts/               # new (empty dir, built-in scripts go here later)
onedep_manager/cli/shell.py                 # new: `shell` Click command
onedep_manager/main.py                      # modify: register `shell` command
tests/shell/__init__.py                     # new (empty)
tests/shell/test_context.py                 # new
tests/shell/test_resolver.py                # new
tests/shell/test_file_filters.py            # new
tests/shell/test_plugin_loader.py           # new
tests/shell/test_scripts.py                 # new
tests/shell/test_bridging.py                # new
tests/shell/test_files.py                   # new
tests/shell/test_app.py                     # new
tests/cli/test_shell.py                     # new
```

---

### Task 1: Add the `cmd2` dependency and bump the Python floor

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `cmd2` importable at `^2.7` in the project's environment; no later task depends on any symbol from this task beyond `import cmd2` working.

- [ ] **Step 1: Edit `pyproject.toml`**

Change:
```toml
[tool.poetry.dependencies]
python = "^3.8"
```
to:
```toml
[tool.poetry.dependencies]
python = "^3.9"
```
and add, alphabetically with the other dependencies:
```toml
cmd2 = "^2.7"
```

- [ ] **Step 2: Create/refresh a local virtualenv and install**

```bash
python3 -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/pip install "cmd2==2.7.0" pytest
```

- [ ] **Step 3: Verify no dependency conflicts and that cmd2 imports**

```bash
./.venv/bin/pip check
./.venv/bin/python -c "import cmd2; print(cmd2.__version__)"
```

Expected: `pip check` reports no broken requirements, and the version prints `2.7.0`. (Verified during planning: cmd2 2.7.0 + this project's `rich<14,>=13` pin install together with zero conflicts — `rich-argparse` only requires `rich>=11.0.0`.)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "Add cmd2 dependency, bump Python floor to 3.9 for embedded shell"
```

---

### Task 2: `ShellContext`

**Files:**
- Create: `onedep_manager/shell/__init__.py` (empty)
- Create: `onedep_manager/shell/context.py`
- Test: `tests/shell/__init__.py` (empty), `tests/shell/test_context.py`

**Interfaces:**
- Produces: `ShellContext` dataclass with fields `current_entry: Optional[str]`, `current_selection: List[Path]`, and methods `set_entry(entry_id: str) -> None`, `set_selection(files: List[Path]) -> None`, `clear_selection() -> None`. Later tasks (`files.py`, `app.py`) read/write these directly.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_context.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_context.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell'`.

- [ ] **Step 3: Create `onedep_manager/shell/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `onedep_manager/shell/context.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ShellContext:
    """Mutable session state for one running `onedep-manager shell` instance."""

    current_entry: Optional[str] = None
    current_selection: List[Path] = field(default_factory=list)

    def set_entry(self, entry_id: str) -> None:
        self.current_entry = entry_id
        self.current_selection = []

    def set_selection(self, files: List[Path]) -> None:
        self.current_selection = list(files)

    def clear_selection(self) -> None:
        self.current_selection = []
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_context.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add onedep_manager/shell/__init__.py onedep_manager/shell/context.py tests/shell/__init__.py tests/shell/test_context.py
git commit -m "Add ShellContext for the embedded shell"
```

---

### Task 3: `EntryPathResolver`

**Files:**
- Create: `onedep_manager/shell/resolver.py`
- Test: `tests/shell/test_resolver.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `UnknownRepositoryError` exception; `EntryPathResolver(path_info=None, site=None)` with `.resolve(entry_id: str, repo: str) -> Path` and `.known_repos -> List[str]`. `files.py` (Task 8) and `app.py` (Task 9) construct and call this.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_resolver.py
from pathlib import Path

import pytest

from onedep_manager.shell.resolver import EntryPathResolver, UnknownRepositoryError


class FakePathInfo:
    """Stands in for wwpdb.io.locator.PathInfo, which isn't installed here."""

    def getTempDepPath(self, dataSetId):
        return f"/data/tempdep/{dataSetId}"

    def getDepositPath(self, dataSetId):
        return f"/data/deposit/{dataSetId}"

    def getDepositUIPath(self, dataSetId):
        return f"/data/deposit-ui/{dataSetId}"

    def getArchivePath(self, dataSetId):
        return f"/data/archive/{dataSetId}"

    def getDirPath(self, dataSetId, fileSource):
        return f"/data/{fileSource}/{dataSetId}"


@pytest.fixture
def resolver():
    return EntryPathResolver(path_info=FakePathInfo())


def test_resolve_archive(resolver):
    assert resolver.resolve("D_1000001", "archive") == Path("/data/archive/D_1000001")


def test_resolve_upload_uses_get_dir_path(resolver):
    assert resolver.resolve("D_1000001", "upload") == Path("/data/uploads/D_1000001")


def test_resolve_unknown_repo_raises(resolver):
    with pytest.raises(UnknownRepositoryError):
        resolver.resolve("D_1000001", "not-a-repo")


def test_known_repos_lists_all_supported_names(resolver):
    assert "archive" in resolver.known_repos
    assert "deposit-ui" in resolver.known_repos


def test_constructing_without_path_info_defers_wwpdb_import():
    # Must not raise ImportError at construction time just because
    # wwpdb.io isn't installed in this environment -- only fails if
    # .resolve() is actually called without an injected path_info.
    resolver = EntryPathResolver.__new__(EntryPathResolver)
    assert resolver is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_resolver.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.resolver'`.

- [ ] **Step 3: Implement `onedep_manager/shell/resolver.py`**

```python
from pathlib import Path
from typing import Callable, Dict, Optional


class UnknownRepositoryError(Exception):
    """Raised when EntryPathResolver.resolve() is asked for an unsupported repo name."""


_REPO_GETTERS: Dict[str, Callable] = {
    "tempdep": lambda pi, entry_id: pi.getTempDepPath(dataSetId=entry_id),
    "deposit": lambda pi, entry_id: pi.getDepositPath(dataSetId=entry_id),
    "deposit-ui": lambda pi, entry_id: pi.getDepositUIPath(dataSetId=entry_id),
    "archive": lambda pi, entry_id: pi.getArchivePath(dataSetId=entry_id),
    "upload": lambda pi, entry_id: pi.getDirPath(dataSetId=entry_id, fileSource="uploads"),
    "pickles": lambda pi, entry_id: pi.getDirPath(dataSetId=entry_id, fileSource="pickles"),
}


class EntryPathResolver:
    """Resolves an entry id + repository name to a filesystem path.

    Wraps wwPDB's PathInfo. The real PathInfo is only imported inside
    __init__ when no `path_info` is injected, so importing this module
    (and constructing a resolver with an injected fake) never requires
    wwpdb.io to be installed -- only calling .resolve() with the real,
    lazily-constructed PathInfo does.
    """

    def __init__(self, path_info=None, site: Optional[str] = None):
        if path_info is None:
            from wwpdb.io.locator.PathInfo import PathInfo

            path_info = PathInfo(siteId=site)
        self._path_info = path_info

    def resolve(self, entry_id: str, repo: str) -> Path:
        try:
            getter = _REPO_GETTERS[repo]
        except KeyError:
            raise UnknownRepositoryError(f"Unknown repository '{repo}'. Valid repositories: {', '.join(sorted(_REPO_GETTERS))}")
        return Path(getter(self._path_info, entry_id))

    @property
    def known_repos(self):
        return sorted(_REPO_GETTERS)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_resolver.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/resolver.py tests/shell/test_resolver.py
git commit -m "Add EntryPathResolver for the embedded shell"
```

---

### Task 4: wwPDB file filtering

**Files:**
- Create: `onedep_manager/shell/file_filters.py`
- Test: `tests/shell/test_file_filters.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `FileAttributes` dataclass (`path: Path`, `dataset: str`, `content_type: str`, `part: int`, `format: str`, `version: int`); `parse_wwpdb_filename(path: Path) -> Optional[FileAttributes]`; `filter_files(files: Sequence[Path], types=None, milestone=None, version=None) -> List[FileAttributes]`. `files.py` (Task 8) calls both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_file_filters.py
from pathlib import Path

from onedep_manager.shell.file_filters import filter_files, parse_wwpdb_filename


def test_parse_valid_filename():
    attrs = parse_wwpdb_filename(Path("D_800000_model_P1.cif.V2"))

    assert attrs.dataset == "D_800000"
    assert attrs.content_type == "model"
    assert attrs.part == 1
    assert attrs.format == "cif"
    assert attrs.version == 2


def test_parse_filename_with_hyphenated_content_type():
    attrs = parse_wwpdb_filename(Path("D_800000_model-upload_P1.cif.V1"))

    assert attrs.content_type == "model-upload"


def test_parse_non_wwpdb_filename_returns_none():
    assert parse_wwpdb_filename(Path("README.md")) is None


def _paths(*names):
    return [Path(n) for n in names]


def test_filter_by_type():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_sf_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
    )

    matched = filter_files(files, types=["model"])

    assert [a.path.name for a in matched] == ["D_800000_model_P1.cif.V1"]


def test_filter_by_multiple_types():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_sf_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
    )

    matched = filter_files(files, types=["model", "model-upload"])

    names = {a.path.name for a in matched}
    assert names == {"D_800000_model_P1.cif.V1", "D_800000_model-upload_P1.cif.V1"}


def test_filter_by_milestone_matches_hyphen_suffix():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
        "D_800000_sf-upload_P1.cif.V1",
    )

    matched = filter_files(files, milestone="upload")

    names = {a.path.name for a in matched}
    assert names == {"D_800000_model-upload_P1.cif.V1", "D_800000_sf-upload_P1.cif.V1"}


def test_filter_by_exact_version():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model_P1.cif.V2",
    )

    matched = filter_files(files, version="1")

    assert [a.version for a in matched] == [1]


def test_filter_by_latest_version_groups_by_dataset_type_part_format():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model_P1.cif.V2",
        "D_800000_model_P1.cif.V3",
        "D_800000_sf_P1.cif.V1",
    )

    matched = filter_files(files, version="latest")

    versions_by_type = {a.content_type: a.version for a in matched}
    assert versions_by_type == {"model": 3, "sf": 1}


def test_filter_skips_unparseable_files():
    files = _paths("D_800000_model_P1.cif.V1", "not_wwpdb.txt")

    matched = filter_files(files, types=["model"])

    assert len(matched) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_file_filters.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.file_filters'`.

- [ ] **Step 3: Implement `onedep_manager/shell/file_filters.py`**

```python
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_FILENAME_RE = re.compile(
    r"^(?P<dataset>D_\d+)_(?P<content_type>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)_P(?P<part>\d+)"
    r"\.(?P<format>[A-Za-z0-9]+)\.V(?P<version>\d+)$"
)


@dataclass(frozen=True)
class FileAttributes:
    path: Path
    dataset: str
    content_type: str
    part: int
    format: str
    version: int


def parse_wwpdb_filename(path: Path) -> Optional[FileAttributes]:
    """Parse a wwPDB-convention filename, e.g. D_800000_model_P1.cif.V2.

    Returns None for filenames that don't match the convention, rather
    than raising, so callers can filter a mixed directory listing.
    """
    match = _FILENAME_RE.match(path.name)
    if not match:
        return None

    return FileAttributes(
        path=path,
        dataset=match.group("dataset"),
        content_type=match.group("content_type"),
        part=int(match.group("part")),
        format=match.group("format"),
        version=int(match.group("version")),
    )


def filter_files(
    files: Sequence[Path],
    types: Optional[Sequence[str]] = None,
    milestone: Optional[str] = None,
    version: Optional[str] = None,
) -> List[FileAttributes]:
    parsed = [a for a in (parse_wwpdb_filename(f) for f in files) if a is not None]

    if types:
        type_set = set(types)
        parsed = [a for a in parsed if a.content_type in type_set]

    if milestone:
        suffix = f"-{milestone}"
        parsed = [a for a in parsed if a.content_type.endswith(suffix)]

    if version == "latest":
        parsed = _latest_only(parsed)
    elif version is not None:
        parsed = [a for a in parsed if a.version == int(version)]

    return parsed


def _latest_only(attrs: List[FileAttributes]) -> List[FileAttributes]:
    latest: Dict[Tuple[str, str, int, str], FileAttributes] = {}

    for a in attrs:
        key = (a.dataset, a.content_type, a.part, a.format)
        if key not in latest or a.version > latest[key].version:
            latest[key] = a

    return list(latest.values())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_file_filters.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/file_filters.py tests/shell/test_file_filters.py
git commit -m "Add wwPDB filename parsing and filtering for the embedded shell"
```

---

### Task 5: Plugin loader

**Files:**
- Create: `onedep_manager/shell/plugin_loader.py`
- Test: `tests/shell/test_plugin_loader.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `FilePlugin` ABC (`name: str`, `help: str`, `run(self, files: list, **kwargs) -> None`); `load_plugins(directories: List[Path]) -> Dict[str, FilePlugin]`. `app.py` (Task 9) calls `load_plugins`; `files.py` (Task 8) dispatches into the returned dict by name.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_plugin_loader.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_plugin_loader.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.plugin_loader'`.

- [ ] **Step 3: Implement `onedep_manager/shell/plugin_loader.py`**

```python
import importlib.util
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class FilePlugin(ABC):
    """Base class for a `files <name>` action plugin.

    Subclasses set `name` (the action name used to invoke it) and `help`
    (shown in `files` usage output), and implement `run`.
    """

    name: str
    help: str = ""

    @abstractmethod
    def run(self, files: list, **kwargs) -> None:
        raise NotImplementedError()


def _load_module(py_file: Path):
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins(directories: List[Path]) -> Dict[str, FilePlugin]:
    """Scan `directories` in order for FilePlugin subclasses.

    A plugin file that fails to import, or a plugin class that fails to
    instantiate, is logged as a warning and skipped -- it never prevents
    the shell from starting or other plugins from loading. Directories
    are scanned in the order given, so a later directory's plugin with
    the same `name` overrides an earlier one (built-ins first, then the
    user's personal directory).
    """
    plugins: Dict[str, FilePlugin] = {}

    for directory in directories:
        if not directory.is_dir():
            continue

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            try:
                module = _load_module(py_file)
            except Exception:
                logger.warning("Failed to load plugin file '%s'", py_file, exc_info=True)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is FilePlugin or not issubclass(obj, FilePlugin):
                    continue

                try:
                    instance = obj()
                except Exception:
                    logger.warning("Failed to instantiate plugin class '%s' from '%s'", obj.__name__, py_file, exc_info=True)
                    continue

                plugins[instance.name] = instance

    return plugins
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_plugin_loader.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/plugin_loader.py tests/shell/test_plugin_loader.py
git commit -m "Add FilePlugin base class and drop-in plugin loader"
```

---

### Task 6: Script registry

**Files:**
- Create: `onedep_manager/shell/scripts.py`
- Test: `tests/shell/test_scripts.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `ScriptNotFoundError`; `ScriptMetadata` dataclass (`name`, `path`, `description`, `tags`); `ScriptRegistry(directories: List[Path])` with `.list(tag: Optional[str] = None) -> List[ScriptMetadata]` and `.run(name: str, args: Optional[List[str]] = None) -> int`. `app.py` (Task 9) constructs and calls this.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_scripts.py
import os
import stat
import textwrap

import pytest

from onedep_manager.shell.scripts import ScriptNotFoundError, ScriptRegistry


def _write_script(directory, name, body, description="", tags=None):
    script_path = directory / name
    script_path.write_text(body)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    sidecar = directory / f"{name}.yaml"
    tags = tags or []
    sidecar.write_text(
        textwrap.dedent(
            f"""
            name: {name}
            description: {description}
            tags: {tags}
            """
        )
    )
    return script_path


def test_list_registered_scripts(tmp_path):
    _write_script(tmp_path, "hello.sh", "#!/bin/sh\necho hi\n", description="says hi", tags=["demo"])

    registry = ScriptRegistry([tmp_path])
    listed = registry.list()

    assert len(listed) == 1
    assert listed[0].name == "hello.sh"
    assert listed[0].description == "says hi"
    assert listed[0].tags == ["demo"]


def test_list_filters_by_tag(tmp_path):
    _write_script(tmp_path, "a.sh", "#!/bin/sh\n", tags=["demo"])
    _write_script(tmp_path, "b.sh", "#!/bin/sh\n", tags=["other"])

    registry = ScriptRegistry([tmp_path])

    assert [s.name for s in registry.list(tag="demo")] == ["a.sh"]
    assert [s.name for s in registry.list(tag="nope")] == []


def test_script_without_sidecar_is_not_registered(tmp_path):
    (tmp_path / "loose.sh").write_text("#!/bin/sh\necho hi\n")

    registry = ScriptRegistry([tmp_path])

    assert registry.list() == []


def test_run_executes_script_and_returns_exit_code(tmp_path, capfd):
    _write_script(tmp_path, "hello.sh", "#!/bin/sh\necho hi\nexit 3\n")

    registry = ScriptRegistry([tmp_path])
    code = registry.run("hello.sh")

    out, _ = capfd.readouterr()
    assert "hi" in out
    assert code == 3


def test_run_passes_arguments(tmp_path, capfd):
    _write_script(tmp_path, "echo_arg.sh", '#!/bin/sh\necho "arg=$1"\n')

    registry = ScriptRegistry([tmp_path])
    registry.run("echo_arg.sh", ["hello"])

    out, _ = capfd.readouterr()
    assert "arg=hello" in out


def test_run_unregistered_script_raises(tmp_path):
    registry = ScriptRegistry([tmp_path])

    with pytest.raises(ScriptNotFoundError):
        registry.run("does-not-exist.sh")


def test_registry_merges_multiple_directories(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()

    _write_script(builtin_dir, "builtin.sh", "#!/bin/sh\n", tags=["builtin"])
    _write_script(user_dir, "user.sh", "#!/bin/sh\n", tags=["user"])

    registry = ScriptRegistry([builtin_dir, user_dir])

    assert {s.name for s in registry.list()} == {"builtin.sh", "user.sh"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_scripts.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.scripts'`.

- [ ] **Step 3: Implement `onedep_manager/shell/scripts.py`**

```python
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ScriptNotFoundError(Exception):
    """Raised when ScriptRegistry.run() is asked for a script that isn't registered."""


@dataclass
class ScriptMetadata:
    name: str
    path: Path
    description: str = ""
    tags: List[str] = field(default_factory=list)


class ScriptRegistry:
    """Discovers whitelisted scripts: presence in one of `directories`, with
    a matching `<script>.yaml` metadata sidecar, is what makes a script
    runnable by name. Nothing outside these directories can be run.
    """

    def __init__(self, directories: List[Path]):
        self._scripts: Dict[str, ScriptMetadata] = {}
        self._discover(directories)

    def _discover(self, directories: List[Path]) -> None:
        for directory in directories:
            if not directory.is_dir():
                continue

            for sidecar in sorted(directory.glob("*.yaml")):
                script_path = sidecar.with_suffix("")
                if not script_path.exists():
                    continue

                with open(sidecar) as f:
                    meta = yaml.safe_load(f) or {}

                name = meta.get("name") or script_path.name
                self._scripts[name] = ScriptMetadata(
                    name=name,
                    path=script_path,
                    description=meta.get("description") or "",
                    tags=list(meta.get("tags") or []),
                )

    def list(self, tag: Optional[str] = None) -> List[ScriptMetadata]:
        scripts = list(self._scripts.values())
        if tag:
            scripts = [s for s in scripts if tag in s.tags]
        return sorted(scripts, key=lambda s: s.name)

    def run(self, name: str, args: Optional[List[str]] = None) -> int:
        try:
            meta = self._scripts[name]
        except KeyError:
            raise ScriptNotFoundError(f"Script '{name}' is not registered")

        command = [str(meta.path)] + list(args or [])
        result = subprocess.run(command)
        return result.returncode
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_scripts.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/scripts.py tests/shell/test_scripts.py
git commit -m "Add whitelisted, tag-searchable script registry for the embedded shell"
```

---

### Task 7: Click-group bridging

**Files:**
- Create: `onedep_manager/shell/bridging.py`
- Test: `tests/shell/test_bridging.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (uses plain `click`/`cmd2`).
- Produces: `bridge_click_group(shell, group: click.Group, ctx_obj=None) -> None`, which sets `do_<group.name>` on `shell`. `app.py` (Task 9) calls this once per existing CLI group.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_bridging.py
import click
import cmd2

from onedep_manager.shell.bridging import bridge_click_group


@click.group(name="demo", help="Demo command group")
def demo_group():
    pass


@demo_group.command(name="greet")
@click.argument("who")
def greet(who):
    click.echo(f"hello {who}")


@demo_group.command(name="boom")
def boom():
    raise click.ClickException("something went wrong")


def _run(shell, line):
    shell.onecmd_plus_hooks(line)


def test_bridged_group_command_runs(capsys):
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    _run(shell, "demo greet world")

    assert "hello world" in capsys.readouterr().out


def test_bridged_group_click_exception_is_shown_not_raised(capsys):
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    _run(shell, "demo boom")  # must not raise

    assert "something went wrong" in capsys.readouterr().err


def test_bridged_command_gets_docstring_from_group_help():
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    assert shell.do_demo.__doc__ == "Demo command group"


def test_bridge_passes_ctx_obj_through():
    seen = {}

    @click.group(name="capture")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    shell = cmd2.Cmd()
    sentinel = object()
    bridge_click_group(shell, capture_group, ctx_obj=sentinel)

    _run(shell, "capture noop")

    assert seen["obj"] is sentinel
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_bridging.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.bridging'`.

- [ ] **Step 3: Implement `onedep_manager/shell/bridging.py`**

```python
import shlex

import click


def bridge_click_group(shell, group: click.Group, ctx_obj=None) -> None:
    """Register `group` as a top-level `do_<group.name>` command on `shell`.

    Delegates straight to the group's own `main()` with standalone_mode
    disabled, so it never calls sys.exit and Click errors are printed
    (not raised) instead of crashing the shell loop.
    """

    def handler(arg) -> None:
        args = shlex.split(str(arg))
        try:
            group.main(args=args, prog_name=group.name, obj=ctx_obj, standalone_mode=False)
        except click.ClickException as exc:
            exc.show()
        except SystemExit:
            pass

    handler.__doc__ = group.help or f"Run {group.name} commands"
    setattr(shell, f"do_{group.name}", handler)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_bridging.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/bridging.py tests/shell/test_bridging.py
git commit -m "Add helper to bridge existing Click command groups into the shell"
```

---

### Task 8: `files` command logic

**Files:**
- Create: `onedep_manager/shell/files.py`
- Test: `tests/shell/test_files.py`

**Interfaces:**
- Consumes: `ShellContext` (Task 2), `EntryPathResolver`/`UnknownRepositoryError` (Task 3), `FileAttributes`/`parse_wwpdb_filename`/`filter_files` (Task 4), `FilePlugin` (Task 5), `Printer` (`onedep_manager/cli/common.py`, existing).
- Produces: `FilesCommands` mixin class with `dispatch(self, argv: List[str]) -> None`. Requires whatever it's mixed into to provide `self.context: ShellContext`, `self.resolver: EntryPathResolver`, `self.plugins: Dict[str, FilePlugin]`, `self.printer: Printer`. `app.py` (Task 9) mixes this in and calls `dispatch()` from `do_files`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_files.py
import hashlib
import os
from io import StringIO
from pathlib import Path

import pytest

from onedep_manager.cli.common import RawPrinter
from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.files import FilesCommands
from onedep_manager.shell.plugin_loader import FilePlugin
from onedep_manager.shell.resolver import EntryPathResolver


class FakePathInfo:
    def getArchivePath(self, dataSetId):
        return str(Path.cwd())  # overridden per-test via monkeypatch/tmp_path chdir


class RecordingPlugin(FilePlugin):
    name = "record"
    help = "Records the files it was called with"

    def __init__(self):
        self.calls = []

    def run(self, files, **kwargs):
        self.calls.append(list(files))


class _App(FilesCommands):
    def __init__(self, context, resolver, plugins, stream):
        self.context = context
        self.resolver = resolver
        self.plugins = plugins
        self.printer = RawPrinter(stream=stream)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "D_800000_model_P1.cif.V1").write_text("model contents")
    (tmp_path / "D_800000_sf_P1.cif.V1").write_text("sf contents")
    (tmp_path / "README.md").write_text("not a wwpdb file")

    stream = StringIO()
    plugin = RecordingPlugin()
    application = _App(
        context=ShellContext(),
        resolver=EntryPathResolver(path_info=FakePathInfo()),
        plugins={"record": plugin},
        stream=stream,
    )
    application._stream = stream
    application._plugin = plugin
    return application


def test_find_lists_matches_without_selecting(app):
    app.dispatch(["find", "--type", "model"])

    output = app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" in output
    assert app.context.current_selection == []


def test_find_with_select_stores_selection(app):
    app.dispatch(["find", "--type", "model", "-s"])

    assert [p.name for p in app.context.current_selection] == ["D_800000_model_P1.cif.V1"]


def test_find_table_includes_md5_column(app):
    app.dispatch(["find", "--type", "model"])

    expected_md5 = hashlib.md5(b"model contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()


def test_list_shows_current_selection(app):
    app.context.set_selection([Path.cwd() / "D_800000_model_P1.cif.V1"])

    app.dispatch(["list"])

    assert "D_800000_model_P1.cif.V1" in app._stream.getvalue()


def test_list_ignores_filter_style_args_and_uses_selection(app):
    app.context.set_selection([Path.cwd() / "D_800000_sf_P1.cif.V1"])

    app.dispatch(["list"])

    assert "D_800000_sf_P1.cif.V1" in app._stream.getvalue()
    assert "D_800000_model_P1.cif.V1" not in app._stream.getvalue()


def test_hash_action_renders_selection_table(app):
    app.context.set_selection([Path.cwd() / "D_800000_model_P1.cif.V1"])

    app.dispatch(["hash"])

    expected_md5 = hashlib.md5(b"model contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()


def test_hash_action_accepts_one_shot_filters(app):
    app.dispatch(["hash", "--type", "sf"])

    expected_md5 = hashlib.md5(b"sf contents").hexdigest()
    assert expected_md5 in app._stream.getvalue()
    # one-shot filters must not mutate the stored selection
    assert app.context.current_selection == []


def test_unknown_action_reports_error(app):
    app.dispatch(["bogus"])

    assert "Unknown files action" in app._stream.getvalue()


def test_dispatch_with_no_args_reports_usage(app):
    app.dispatch([])

    assert "Usage: files" in app._stream.getvalue()


def test_dispatch_to_plugin_passes_current_selection(app):
    selection = [Path.cwd() / "D_800000_model_P1.cif.V1"]
    app.context.set_selection(selection)

    app.dispatch(["record"])

    assert app._plugin.calls == [selection]


def test_invalid_flag_reports_error_without_crashing(app):
    # argparse's default parser calls sys.exit() on a bad flag, which would
    # kill the whole shell process on a user typo -- this must instead be
    # reported like any other files error.
    app.dispatch(["find", "--not-a-real-flag"])

    assert "files find" in app._stream.getvalue()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_files.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.files'`.

- [ ] **Step 3: Implement `onedep_manager/shell/files.py`**

```python
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

    Composed into onedep_manager.shell.app.OneDepShell. Requires the host
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

        has_filters = any([parsed.type_, parsed.milestone, parsed.version, parsed.entry])

        if has_filters:
            types = parsed.type_.split(",") if parsed.type_ else None
            files = self._candidate_files(parsed.entry, parsed.repo)
            matched = filter_files(files, types=types, milestone=parsed.milestone, version=parsed.version)
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
            self.printer.error("Usage: files <find|list|hash|info|plugin-name> [args...]")
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

        plugin.run(self.context.current_selection)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_files.py -v
```
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/files.py tests/shell/test_files.py
git commit -m "Add files find/list/hash/info commands with plugin dispatch"
```

---

### Task 9: `OneDepShell` app

**Files:**
- Create: `onedep_manager/shell/app.py`
- Test: `tests/shell/test_app.py`

**Interfaces:**
- Consumes: `ShellContext` (Task 2), `EntryPathResolver` (Task 3), `load_plugins`/`FilePlugin` (Task 5), `ScriptRegistry`/`ScriptNotFoundError` (Task 6), `bridge_click_group` (Task 7), `FilesCommands` (Task 8), `CLIContext`/`ConsolePrinter` (existing `onedep_manager/cli/common.py`), `Config` (existing `onedep_manager/config.py`).
- Produces: `OneDepShell(cmd2.Cmd)` class. `onedep_manager/cli/shell.py` (Task 10) constructs and calls `.cmdloop()` on it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_app.py
from pathlib import Path
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


def test_bridges_successfully_importable_group(tmp_path, capsys):
    shell = _shell(
        tmp_path,
        cli_group_imports=[("fakegroup", "tests.shell.fixtures.fake_group_module", "fakegroup")],
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


def test_scripts_list_and_run(tmp_path, capsys):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "hello.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    (scripts_dir / "hello.sh.yaml").write_text("name: hello.sh\ndescription: greets\ntags: [demo]\n")

    shell = _shell(tmp_path)

    shell.do_scripts("list --tag demo")
    assert "hello.sh" in capsys.readouterr().out

    shell.do_scripts("run hello.sh")
    assert "hi" in capsys.readouterr().out


def test_scripts_run_unregistered_reports_error(tmp_path, capsys):
    shell = _shell(tmp_path)

    shell.do_scripts("run does-not-exist")

    assert "not registered" in capsys.readouterr().out or "not registered" in capsys.readouterr().err
```

Add the fixture module used by `test_bridges_successfully_importable_group`:

```python
# tests/shell/fixtures/__init__.py
```

```python
# tests/shell/fixtures/fake_group_module.py
import click


@click.group(name="fakegroup")
def fakegroup():
    pass


@fakegroup.command(name="ping")
def ping():
    click.echo("pong")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_app.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.app'`.

- [ ] **Step 3: Implement `onedep_manager/shell/app.py`**

```python
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
        self.printer = ConsolePrinter(console=Console())
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
                tag = rest[rest.index("--tag") + 1]
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
            if code != 0:
                self.printer.error(f"Script exited with code {code}")
            return

        self.printer.error(f"Unknown scripts action '{action}'")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_app.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/app.py tests/shell/test_app.py tests/shell/fixtures/__init__.py tests/shell/fixtures/fake_group_module.py
git commit -m "Add OneDepShell cmd2 app wiring context, bridging, files, and scripts"
```

---

### Task 10: `onedep-manager shell` Click command

**Files:**
- Create: `onedep_manager/cli/shell.py`
- Modify: `onedep_manager/main.py`
- Create: `onedep_manager/shell/plugins/.gitkeep`, `onedep_manager/shell/scripts/.gitkeep` (placeholder files so git tracks these empty directories)
- Test: `tests/cli/test_shell.py`

**Interfaces:**
- Consumes: `OneDepShell` (Task 9), `get_config`/`CLIContext` (existing `onedep_manager/cli/common.py`).
- Produces: `shell` Click command, registered on the root `cli` group as `onedep-manager shell`.

Note: `onedep_manager/shell/plugins/` and `onedep_manager/shell/scripts/` must stay plain data directories (scanned by path, never imported as Python packages) — no `__init__.py` in either, matching the design in the spec. Use `.gitkeep` placeholder files so git tracks the empty directories.

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_shell.py
from unittest import mock

from click.testing import CliRunner

from onedep_manager.cli.common import CLIContext
from onedep_manager.cli.shell import shell


def test_shell_command_constructs_and_runs_cmdloop():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepShell") as MockShell:
        instance = MockShell.return_value
        result = runner.invoke(shell, [], obj=CLIContext(config=mock.Mock()))

    assert result.exit_code == 0
    instance.cmdloop.assert_called_once()


def test_shell_command_passes_site_option_through():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepShell") as MockShell:
        runner.invoke(shell, ["--site", "WWPDB_DEPLOY_TEST_RU"], obj=CLIContext(config=mock.Mock()))

    _, kwargs = MockShell.call_args
    assert kwargs["site"] == "WWPDB_DEPLOY_TEST_RU"


def test_shell_help():
    runner = CliRunner()
    result = runner.invoke(shell, ["--help"])

    assert result.exit_code == 0
    assert "shell" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/bin/python -m pytest tests/cli/test_shell.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.cli.shell'`.

- [ ] **Step 3: Create the placeholder plugin/script directories**

```bash
mkdir -p onedep_manager/shell/plugins onedep_manager/shell/scripts
touch onedep_manager/shell/plugins/.gitkeep onedep_manager/shell/scripts/.gitkeep
```

- [ ] **Step 4: Implement `onedep_manager/cli/shell.py`**

```python
import click

from onedep_manager.cli.common import get_config
from onedep_manager.shell.app import OneDepShell


@click.command(name="shell", help="Launch the interactive OneDep shell")
@click.option("-i", "--site", "site", help="wwPDB site ID (e.g. WWPDB_DEPLOY_TEST_RU). Defaults to the current site.")
@click.pass_context
def shell(ctx, site):
    config = get_config(ctx)
    OneDepShell(config=config, site=site).cmdloop()
```

- [ ] **Step 5: Register the command in `onedep_manager/main.py`**

```python
from onedep_manager.cli.shell import shell
```
(add alongside the other `from onedep_manager.cli.* import *_group` lines)

```python
cli.add_command(shell)
```
(add alongside the other `cli.add_command(...)` lines)

- [ ] **Step 6: Run test to verify it passes**

```bash
./.venv/bin/python -m pytest tests/cli/test_shell.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Smoke-test the full CLI wiring**

```bash
./.venv/bin/python -m onedep_manager.main --help
```
Expected: `shell` appears in the listed commands, and the process doesn't crash on import (confirms `main.py`'s new import doesn't break at module load, even in this environment's reduced dependency set — `onedep_manager/shell/app.py` only imports `onedep_manager.cli.services/packages/paths` lazily via `importlib.import_module` inside `_bridge_cli_groups`, not at module load time).

- [ ] **Step 8: Commit**

```bash
git add onedep_manager/cli/shell.py onedep_manager/main.py onedep_manager/shell/plugins/.gitkeep onedep_manager/shell/scripts/.gitkeep tests/cli/test_shell.py
git commit -m "Register onedep-manager shell command"
```

---

## Final verification

- [ ] Run the full new-code test surface together:

```bash
./.venv/bin/python -m pytest tests/shell/ tests/cli/test_shell.py -v
```
Expected: all tests pass (58 tests across Tasks 2-10: 4+5+9+6+7+4+12+8 in `tests/shell/` plus 3 in `tests/cli/test_shell.py`).

- [ ] Confirm the pre-existing, unrelated collection errors are unchanged (still 4, still the same 4 files):

```bash
./.venv/bin/python -m pytest -q 2>&1 | tail -15
```
Expected: the same `tests/test_packages.py`, `tests/cli/test_packages.py`, `tests/cli/test_services.py`, `tests/services/test_dispatcher.py` collection errors as before this plan (missing `git`/`paramiko` in this environment) — nothing new.

- [ ] Run `ruff check` on everything this plan touched, if `ruff` is available:

```bash
./.venv/bin/pip install ruff
./.venv/bin/ruff check onedep_manager/shell/ onedep_manager/cli/shell.py onedep_manager/main.py
```
