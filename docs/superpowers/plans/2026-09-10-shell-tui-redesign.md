# Shell TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `cmd2`-based `onedep-manager shell` with a Textual TUI that adds a persistent header panel (current entry + file selection) above a scrolling output log, while preserving every existing command and behavior.

**Architecture:** A new `onedep_manager/shell/tui/` subpackage holds the Textual-specific presentation layer (`OneDepTuiApp`, panel widgets, a `TextualPrinter`). Everything under `onedep_manager/shell/` outside `tui/` — `context.py`, `resolver.py`, `file_filters.py`, `plugin_loader.py`, `scripts.py`, `files.py` — is untouched; it was already fully decoupled from `cmd2`. `bridging.py` is adapted (its `setattr`-based `cmd2` registration is replaced with a plain invocation function). `cmd2` is dropped as a dependency.

**Tech Stack:** `textual` (new dependency, exact-pinned), existing `click`, `rich`, `pyyaml`; `pytest-asyncio` (new dev dependency, for Textual's async test harness).

**Spec:** `docs/superpowers/specs/2026-09-10-shell-tui-redesign-design.md`

## Global Constraints

- **Exact dependency pins, verified empirically during planning (not from docs alone):**
  - `textual = "==6.2.1"` — the newest Textual release still requiring only `rich>=13.3.3` (compatible with this project's existing `rich = "^13.0"` pin). Confirmed via `pip download` + reading wheel `METADATA`: Textual `6.3.0` jumps to `rich>=14.2.0`, which conflicts. A caret range (`^6.2`) is **not** safe here — the break is inside the 6.x major line, so caret wouldn't protect against resolving to `6.3.0+`. Use the exact pin.
  - `pytest-asyncio = "^0.23"` (dev-only) — resolves to `0.23.8`, the newest release compatible with this project's `pytest = "^7.4"` (`0.24.0`+ requires `pytest>=8.2`, which conflicts) and `python = "^3.9"`.
  - No Python floor change needed this time — Textual requires `>=3.9,<4.0`, already satisfied by this project's floor (bumped for `cmd2` previously).
  - Verified together: `textual==6.2.1` + `rich>=13.3.3,<14.0` (resolves to `13.9.4`) + `pytest==7.4.4` + `pytest-asyncio==0.23.8` install with zero conflicts (`pip check` clean) and a real `async def test_...` using `App.run_test()`/`Pilot.press()` passes end-to-end.
- **`App.suspend()` raises `SuspendNotSupported` under the headless test harness** (`App.run_test()`). Confirmed by direct reproduction. Any dispatch path that calls `self.suspend()` (bridged Click commands, `!<cmd>` shell delegation, `scripts run`) must be exercised in tests with `monkeypatch.setattr(app, "suspend", lambda: contextlib.nullcontext())` — never call the real `suspend()` in a test. Production code must also catch `SuspendNotSupported` itself and report a clean error via the printer, not let it propagate — some real environments may not support it either.
- **`textual.widgets.Input`'s reactive `value`/`cursor_position` attributes require an active running app context** (`self.app` is touched by their watchers). Confirmed by direct reproduction: constructing a bare `Input()`/`HistoryInput()` and setting `.value` outside a mounted app raises `NoActiveAppError`. Every test that sets `.value` (directly or via `pilot.press(...)`) must do so inside `async with app.run_test():`.
- **`Static` widgets (used for panels) have no public `.renderable` accessor** for reading back what was passed to `.update()` — confirmed by inspection (the real content lives in a private `_render_content`-style attribute, not documented API). Panel tests must not depend on reading widget internals: verify panel content via the pure formatting function directly, and verify the widget calls `.update(...)` correctly by monkeypatching `.update` on the instance (this can be done on a bare, unmounted `Panel()`/`Static()` instance — only reactive-attribute assignment needs a mounted app, plain method calls and monkeypatched methods do not).
- **Mixing the existing `FilesCommands` class with Textual's `App` works with no metaclass/MRO conflict** — confirmed by direct reproduction (`class OneDepTuiApp(FilesCommands, App)` composes cleanly, same pattern as the old `class OneDepShell(FilesCommands, cmd2.Cmd)`).
- Reuse the existing `Printer` ABC (`onedep_manager/cli/common.py`) — `TextualPrinter` is a new third implementation alongside `ConsolePrinter`/`RawPrinter`, not a new abstraction.
- Run only the test file(s) each task adds/touches, not the whole suite, until the Final Verification section — the whole suite has the same pre-existing, environment-dependent `Config()` failures documented in the original shell plan (unrelated to this work).
- Every new/modified `.py` file must stay under this project's ruff line-length (200) and lint rules (`E`, `F`, `B`) — run `ruff check` before each commit. The original shell plan's task reviews found and fixed several unused-import lint failures that slipped through when this wasn't checked; do not repeat that gap.

---

## File Structure

```
pyproject.toml                                      # modify: drop cmd2, add textual + pytest-asyncio
onedep_manager/shell/app.py                          # DELETE (cmd2-based, replaced)
tests/shell/test_app.py                              # DELETE (cmd2-based, replaced)
tests/shell/test_bridging.py                         # DELETE (tests the old cmd2-coupled bridge_click_group; replaced by Task 5)
onedep_manager/shell/bridging.py                     # modify: bridge_click_group -> invoke_click_group
tests/shell/test_bridging.py                         # re-created (Task 5): tests invoke_click_group
onedep_manager/shell/tui/__init__.py                 # new (empty)
onedep_manager/shell/tui/printer.py                  # new: TextualPrinter
onedep_manager/shell/tui/panels.py                   # new: format_entry_panel, Panel, EntrySelectionPanel
onedep_manager/shell/tui/input.py                    # new: HistoryInput
onedep_manager/shell/tui/app.py                      # new: OneDepTuiApp
onedep_manager/cli/shell.py                          # modify: launch OneDepTuiApp instead of OneDepShell
tests/cli/test_shell.py                              # modify: mock OneDepTuiApp, assert .run() not .cmdloop()
tests/shell/tui/__init__.py                          # new (empty)
tests/shell/tui/test_printer.py                      # new
tests/shell/tui/test_panels.py                       # new
tests/shell/tui/test_input.py                        # new
tests/shell/tui/test_app.py                          # new
```

---

### Task 1: Drop `cmd2`, add `textual`/`pytest-asyncio`, remove the old `cmd2`-based shell

**Files:**
- Modify: `pyproject.toml`
- Delete: `onedep_manager/shell/app.py`
- Delete: `tests/shell/test_app.py`
- Delete: `tests/shell/test_bridging.py`

**Interfaces:**
- Produces: `textual` importable at `==6.2.1`, `pytest-asyncio` importable at `^0.23`, in the project's environment. No later task depends on any symbol from the deleted files.

- [ ] **Step 1: Edit `pyproject.toml`**

In `[tool.poetry.dependencies]`, remove the `cmd2 = "^2.7"` line and add (alphabetically):
```toml
textual = "==6.2.1"
```
In `[tool.poetry.group.dev.dependencies]`, add:
```toml
pytest-asyncio = "^0.23"
```

- [ ] **Step 2: Delete the old cmd2-based shell app and its tests**

```bash
git rm onedep_manager/shell/app.py tests/shell/test_app.py tests/shell/test_bridging.py
```

- [ ] **Step 3: Update the venv**

```bash
./.venv/bin/pip uninstall -y cmd2
./.venv/bin/pip install "textual==6.2.1" "pytest-asyncio==0.23.8"
./.venv/bin/pip check
```

- [ ] **Step 4: Verify no dependency conflicts and that textual imports**

```bash
./.venv/bin/python -c "import textual; print(textual.__version__)"
./.venv/bin/python -c "import rich; print(rich.__version__)"
```
Expected: `pip check` reports no broken requirements; textual prints `6.2.1`; rich prints something in the `13.x` range (verified during planning: `13.9.4`).

- [ ] **Step 5: Confirm the rest of the shell suite still collects (minus what was deleted)**

```bash
./.venv/bin/python -m pytest tests/shell/ tests/cli/test_shell.py -v 2>&1 | tail -30
```
Expected: `tests/shell/test_bridging.py` and `tests/shell/test_app.py` are gone from the collected set (deleted). `tests/cli/test_shell.py` will now fail to **collect** (`ModuleNotFoundError`) — not just fail its assertions — because `onedep_manager/cli/shell.py` still does `from onedep_manager.shell.app import OneDepShell` at module level, and that module no longer exists after this step. This is expected and isolated to this one file (pytest reports it as a per-file collection error, same as this project's existing pre-existing collection/failure pattern; it does not block any other test file from collecting or running) — it stays broken until Task 7 updates `cli/shell.py` to import `OneDepTuiApp` instead. Every other file in `tests/shell/` should still pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml
git commit -m "Drop cmd2, add textual + pytest-asyncio; remove the old cmd2-based shell app"
```

---

### Task 2: `TextualPrinter`

**Files:**
- Create: `onedep_manager/shell/tui/__init__.py` (empty)
- Create: `onedep_manager/shell/tui/printer.py`
- Create: `tests/shell/tui/__init__.py` (empty)
- Create: `tests/shell/tui/test_printer.py`

**Interfaces:**
- Consumes: `Printer` (ABC, `onedep_manager/cli/common.py`, existing).
- Produces: `TextualPrinter(Printer)` with `__init__(self, log)` where `log` is any object with a `.write(renderable)` method (duck-typed — the real caller passes a `textual.widgets.RichLog`, tests pass a fake). Later tasks (`OneDepTuiApp`) construct `TextualPrinter(self.query_one(RichLog))`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/tui/test_printer.py
from rich.table import Table
from rich.text import Text

from onedep_manager.shell.tui.printer import TextualPrinter


class FakeLog:
    def __init__(self):
        self.written = []

    def write(self, content):
        self.written.append(content)


def test_info_writes_styled_text():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.info("hello")

    assert len(log.written) == 1
    written = log.written[0]
    assert isinstance(written, Text)
    assert written.plain == "⬢ hello"
    assert written.style == "slate_blue3"


def test_error_writes_styled_text():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.error("something broke")

    written = log.written[0]
    assert isinstance(written, Text)
    assert written.plain == "⬢ something broke"
    assert written.style == "indian_red"


def test_table_writes_a_rich_table_with_header_and_rows():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.table(["a", "b"], [["1", "2"], ["3", "4"]])

    assert len(log.written) == 1
    written = log.written[0]
    assert isinstance(written, Table)
    assert [col.header for col in written.columns] == ["a", "b"]
    assert written.row_count == 2


def test_json_writes_a_json_renderable():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.json({"foo": "bar"})

    assert len(log.written) == 1
    # rich.json.JSON renders from the data it was built with; just confirm
    # the right type reached the log, formatting is rich's own concern.
    from rich.json import JSON

    assert isinstance(log.written[0], JSON)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_printer.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.tui'` (or `.printer`).

- [ ] **Step 3: Create `onedep_manager/shell/tui/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `onedep_manager/shell/tui/printer.py`**

```python
from rich.json import JSON
from rich.table import Table
from rich.text import Text

from onedep_manager.cli.common import Printer


class TextualPrinter(Printer):
    """Printer implementation that writes into a Textual log widget.

    `log` is duck-typed to anything with a `.write(renderable)` method
    (the real caller passes a `textual.widgets.RichLog`) so this stays
    testable without mounting a real Textual app.
    """

    def __init__(self, log):
        self._log = log

    def json(self, data: dict) -> None:
        self._log.write(JSON.from_data(data))

    def table(self, header: list, data: list) -> None:
        table = Table(show_header=True, header_style="bold blue")
        for col in header:
            table.add_column(col)
        for row in data:
            table.add_row(*row)
        self._log.write(table)

    def info(self, message) -> None:
        self._log.write(Text(f"⬢ {message}", style="slate_blue3"))

    def error(self, message) -> None:
        self._log.write(Text(f"⬢ {message}", style="indian_red"))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_printer.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add onedep_manager/shell/tui/__init__.py onedep_manager/shell/tui/printer.py tests/shell/tui/__init__.py tests/shell/tui/test_printer.py
git commit -m "Add TextualPrinter for the shell TUI"
```

---

### Task 3: Panel system

**Files:**
- Create: `onedep_manager/shell/tui/panels.py`
- Create: `tests/shell/tui/test_panels.py`

**Interfaces:**
- Consumes: `ShellContext` (`onedep_manager/shell/context.py`, existing).
- Produces: `format_entry_panel(context: ShellContext, max_names: int = 10) -> str`; `Panel(Static)` base widget with `refresh_from_context(self, context: ShellContext) -> None`; `EntrySelectionPanel(Panel)`. `OneDepTuiApp` (Task 6) composes an `EntrySelectionPanel` and calls `refresh_from_context` on every `Panel` it finds after each command.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/tui/test_panels.py
from pathlib import Path

from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.tui.panels import EntrySelectionPanel, Panel, format_entry_panel


def test_format_entry_panel_with_no_entry_and_no_selection():
    context = ShellContext()

    text = format_entry_panel(context)

    assert "no entry set" in text
    assert "no files selected" in text


def test_format_entry_panel_with_entry_and_no_selection():
    context = ShellContext()
    context.set_entry("D_1000001")

    text = format_entry_panel(context)

    assert "D_1000001" in text
    assert "no files selected" in text


def test_format_entry_panel_lists_selected_filenames():
    context = ShellContext()
    context.set_entry("D_1000001")
    context.set_selection([Path("/a/one.cif"), Path("/a/two.cif")])

    text = format_entry_panel(context)

    assert "one.cif" in text
    assert "two.cif" in text
    assert "more" not in text


def test_format_entry_panel_truncates_past_max_names():
    context = ShellContext()
    context.set_entry("D_1000001")
    context.set_selection([Path(f"/a/file{i}.cif") for i in range(15)])

    text = format_entry_panel(context, max_names=10)

    for i in range(10):
        assert f"file{i}.cif" in text
    for i in range(10, 15):
        assert f"file{i}.cif" not in text
    assert "... 5 more" in text


def test_entry_selection_panel_is_a_panel():
    panel = EntrySelectionPanel()
    assert isinstance(panel, Panel)


def test_entry_selection_panel_refresh_calls_update_with_formatted_text(monkeypatch):
    panel = EntrySelectionPanel()
    calls = []
    monkeypatch.setattr(panel, "update", lambda content: calls.append(content))
    context = ShellContext()
    context.set_entry("D_1000001")

    panel.refresh_from_context(context)

    assert calls == [format_entry_panel(context)]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_panels.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.tui.panels'`.

- [ ] **Step 3: Implement `onedep_manager/shell/tui/panels.py`**

```python
from textual.widgets import Static

from onedep_manager.shell.context import ShellContext


def format_entry_panel(context: ShellContext, max_names: int = 10) -> str:
    entry = context.current_entry or "no entry set"
    selection = context.current_selection

    if not selection:
        selection_text = "no files selected"
    else:
        names = [p.name for p in selection[:max_names]]
        remainder = len(selection) - len(names)
        selection_text = ", ".join(names)
        if remainder > 0:
            selection_text += f", ... {remainder} more"

    return f"Entry: {entry}\nSelection: {selection_text}"


class Panel(Static):
    """Base class for a header panel widget.

    Subclasses implement `refresh_from_context`, called by the app after
    every command so the panel reflects current shell state.
    """

    def refresh_from_context(self, context: ShellContext) -> None:
        raise NotImplementedError()


class EntrySelectionPanel(Panel):
    """Shows the current entry and current file selection (truncated)."""

    def refresh_from_context(self, context: ShellContext) -> None:
        self.update(format_entry_panel(context))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_panels.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/tui/panels.py tests/shell/tui/test_panels.py
git commit -m "Add panel system (format_entry_panel, Panel, EntrySelectionPanel) for the shell TUI"
```

---

### Task 4: `HistoryInput`

**Files:**
- Create: `onedep_manager/shell/tui/input.py`
- Create: `tests/shell/tui/test_input.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (uses only `textual`).
- Produces: `HistoryInput(Input)` with `add_to_history(self, command: str) -> None`, `action_history_prev(self) -> None`, `action_history_next(self) -> None`, bound to Up/Down keys. `OneDepTuiApp` (Task 6) composes one and calls `add_to_history` on submit.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/tui/test_input.py
import pytest
from textual.app import App, ComposeResult

from onedep_manager.shell.tui.input import HistoryInput


class _HistoryInputTestApp(App):
    def compose(self) -> ComposeResult:
        yield HistoryInput(id="cmdline")


@pytest.mark.asyncio
async def test_up_recalls_most_recent_command():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")

        assert input_widget.value == "entry D_1000001"


@pytest.mark.asyncio
async def test_up_up_recalls_further_back():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")
        await pilot.press("up")

        assert input_widget.value == "files find"


@pytest.mark.asyncio
async def test_up_past_the_oldest_entry_stays_on_oldest():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")

        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("up")

        assert input_widget.value == "files find"


@pytest.mark.asyncio
async def test_down_after_up_returns_toward_empty():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("down")
        await pilot.press("down")

        assert input_widget.value == ""


@pytest.mark.asyncio
async def test_up_with_no_history_does_nothing():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)

        await pilot.press("up")

        assert input_widget.value == ""


def test_add_to_history_skips_consecutive_duplicates():
    input_widget = HistoryInput.__new__(HistoryInput)
    input_widget._history = []
    input_widget._history_index = None

    input_widget.add_to_history("files find")
    input_widget.add_to_history("files find")

    assert input_widget._history == ["files find"]


def test_add_to_history_ignores_empty_command():
    input_widget = HistoryInput.__new__(HistoryInput)
    input_widget._history = []
    input_widget._history_index = None

    input_widget.add_to_history("")

    assert input_widget._history == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_input.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.tui.input'`.

- [ ] **Step 3: Implement `onedep_manager/shell/tui/input.py`**

```python
from typing import List, Optional

from textual.binding import Binding
from textual.widgets import Input


class HistoryInput(Input):
    """An Input with up/down command history recall."""

    BINDINGS = [
        Binding("up", "history_prev", "Previous command", show=False),
        Binding("down", "history_next", "Next command", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history: List[str] = []
        self._history_index: Optional[int] = None

    def add_to_history(self, command: str) -> None:
        if command and (not self._history or self._history[-1] != command):
            self._history.append(command)
        self._history_index = None

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._history_index is None:
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        self.value = self._history[self._history_index]

    def action_history_next(self) -> None:
        if self._history_index is None:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.value = self._history[self._history_index]
        else:
            self._history_index = None
            self.value = ""
```

Note: `test_add_to_history_skips_consecutive_duplicates` and
`test_add_to_history_ignores_empty_command` construct via
`HistoryInput.__new__` rather than `HistoryInput()` specifically to avoid
`Input.__init__`'s reactive setup, since `add_to_history` alone doesn't
touch any reactive attribute and doesn't need a mounted app — this keeps
those two tests fast or app-independent. All the Up/Down key tests do
need `run_test()`, since pressing a key ultimately sets `.value`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_input.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/tui/input.py tests/shell/tui/test_input.py
git commit -m "Add HistoryInput (up/down command recall) for the shell TUI"
```

---

### Task 5: `bridging.py` rewrite

**Files:**
- Modify: `onedep_manager/shell/bridging.py`
- Create: `tests/shell/test_bridging.py` (deleted in Task 1, re-created here with new content)

**Interfaces:**
- Consumes: nothing from earlier tasks (uses only `click`).
- Produces: `invoke_click_group(group: click.Group, args: list, ctx_obj=None) -> None`, replacing the old `bridge_click_group(shell, group, ctx_obj=None)`. `OneDepTuiApp` (Task 6) calls this inside `with self.suspend(): ...`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/test_bridging.py
import click

from onedep_manager.shell.bridging import invoke_click_group


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


def test_invoke_runs_the_command(capsys):
    invoke_click_group(demo_group, ["greet", "world"])

    assert "hello world" in capsys.readouterr().out


def test_invoke_shows_click_exception_instead_of_raising(capsys):
    invoke_click_group(demo_group, ["boom"])  # must not raise

    assert "something went wrong" in capsys.readouterr().err


def test_invoke_passes_ctx_obj_through():
    seen = {}

    @click.group(name="capture")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    sentinel = object()

    invoke_click_group(capture_group, ["noop"], ctx_obj=sentinel)

    assert seen["obj"] is sentinel


def test_invoke_with_no_ctx_obj_defaults_to_none():
    seen = {}

    @click.group(name="capture2")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    invoke_click_group(capture_group, ["noop"])

    assert seen["obj"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/test_bridging.py -v
```
Expected: FAIL — `invoke_click_group` doesn't exist yet (`ImportError`).

- [ ] **Step 3: Rewrite `onedep_manager/shell/bridging.py`**

```python
import click


def invoke_click_group(group: click.Group, args: list, ctx_obj=None) -> None:
    """Run `group` with `args`, handling Click's own exit/error paths.

    Delegates to the group's own main() with standalone_mode disabled, so
    it never calls sys.exit and Click errors are shown (not raised)
    instead of propagating.
    """
    try:
        group.main(args=args, prog_name=group.name, obj=ctx_obj, standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
    except SystemExit:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/test_bridging.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/bridging.py tests/shell/test_bridging.py
git commit -m "Replace bridge_click_group with invoke_click_group for the TUI shell"
```

---

### Task 6: `OneDepTuiApp`

**Files:**
- Create: `onedep_manager/shell/tui/app.py`
- Create: `tests/shell/tui/test_app.py`

**Interfaces:**
- Consumes: `ShellContext` (Task 2 in the original plan — existing), `EntryPathResolver` (existing), `load_plugins` (existing), `ScriptRegistry`/`ScriptNotFoundError` (existing), `FilesCommands` (existing, mixed in), `invoke_click_group` (Task 5), `TextualPrinter` (Task 2), `Panel`/`EntrySelectionPanel` (Task 3), `HistoryInput` (Task 4), `CLIContext` (`onedep_manager/cli/common.py`, existing), `Config` (`onedep_manager/config.py`, existing).
- Produces: `OneDepTuiApp(FilesCommands, App)` class. `onedep_manager/cli/shell.py` (Task 7) constructs and calls `.run()` on it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/shell/tui/test_app.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_app.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'onedep_manager.shell.tui.app'`.

- [ ] **Step 3: Implement `onedep_manager/shell/tui/app.py`**

```python
import importlib
import logging
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

logger = logging.getLogger(__name__)

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
        border: solid $accent;
        padding: 0 1;
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
        self._resolve_cli_groups()
        self._refresh_panels()
        self.query_one("#cmdline", HistoryInput).focus()

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

        if stripped.startswith("!"):
            self._run_suspended(f"! {stripped[1:]}", lambda: subprocess.run(stripped[1:], shell=True))
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

        self._refresh_panels()

    def _run_suspended(self, label: str, action) -> None:
        try:
            with self.suspend():
                action()
        except SuspendNotSupported:
            self.printer.error(f"Cannot run '{label}' here: suspending the TUI isn't supported in this environment")

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
            if code != 0:
                self.printer.error(f"Script exited with code {code}")
            return

        self.printer.error(f"Unknown scripts action '{action}'")

    def _run_script(self, name: str, args: List[str]) -> int:
        result = {}

        def _run():
            result["code"] = self.scripts.run(name, args)

        try:
            with self.suspend():
                _run()
        except SuspendNotSupported:
            self.printer.error(f"Cannot run script '{name}' here: suspending the TUI isn't supported in this environment")
            return 0
        return result["code"]
```

Note: `_run_script` is separate from the generic `_run_suspended` helper
because it needs to propagate `ScriptNotFoundError`/`OSError`/
`PermissionError` out to `_do_scripts`'s own except clauses (which report
different messages per exception type), while `_run_suspended` is for the
simpler fire-and-forget cases (`!<cmd>`, bridged Click groups) that only
ever need the generic `SuspendNotSupported` guard.

- [ ] **Step 4: Run tests to verify they pass**

```bash
./.venv/bin/python -m pytest tests/shell/tui/test_app.py -v
```
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add onedep_manager/shell/tui/app.py tests/shell/tui/test_app.py
git commit -m "Add OneDepTuiApp: the Textual shell app wiring context, panels, and dispatch"
```

---

### Task 7: Wire `onedep-manager shell` to the new app

**Files:**
- Modify: `onedep_manager/cli/shell.py`
- Modify: `tests/cli/test_shell.py`

**Interfaces:**
- Consumes: `OneDepTuiApp` (Task 6).
- Produces: the `shell` Click command now launches `OneDepTuiApp` instead of the deleted `OneDepShell`.

- [ ] **Step 1: Update the failing tests**

```python
# tests/cli/test_shell.py
from unittest import mock

from click.testing import CliRunner

from onedep_manager.cli.common import CLIContext
from onedep_manager.cli.shell import shell


def test_shell_command_constructs_and_runs():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepTuiApp") as MockApp:
        instance = MockApp.return_value
        result = runner.invoke(shell, [], obj=CLIContext(config=mock.Mock()))

    assert result.exit_code == 0
    instance.run.assert_called_once()


def test_shell_command_passes_site_option_through():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepTuiApp") as MockApp:
        runner.invoke(shell, ["--site", "WWPDB_DEPLOY_TEST_RU"], obj=CLIContext(config=mock.Mock()))

    _, kwargs = MockApp.call_args
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
Expected: FAIL — `onedep_manager.cli.shell.OneDepTuiApp` doesn't exist yet (patch target error), since `cli/shell.py` still imports the deleted `OneDepShell`.

- [ ] **Step 3: Update `onedep_manager/cli/shell.py`**

```python
import click

from onedep_manager.cli.common import get_config
from onedep_manager.shell.tui.app import OneDepTuiApp


@click.command(name="shell", help="Launch the interactive OneDep shell")
@click.option("-i", "--site", "site", help="wwPDB site ID (e.g. WWPDB_DEPLOY_TEST_RU). Defaults to the current site.")
@click.pass_context
def shell(ctx, site):
    config = get_config(ctx)
    OneDepTuiApp(config=config, site=site).run()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./.venv/bin/python -m pytest tests/cli/test_shell.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Smoke-test the full CLI wiring**

```bash
./.venv/bin/python -m onedep_manager.main --help
```
Expected: `shell` still appears in the listed commands, process doesn't crash on import. `onedep_manager/shell/tui/app.py` only imports `onedep_manager.cli.services`/`packages`/`paths` lazily via `importlib.import_module` inside `_resolve_cli_groups`, not at module load time, same as the previous `cmd2`-based app did — so this works in this environment even without `paramiko`/`gitpython` fully set up, same as before.

- [ ] **Step 6: Commit**

```bash
git add onedep_manager/cli/shell.py tests/cli/test_shell.py
git commit -m "Wire onedep-manager shell to launch OneDepTuiApp"
```

---

## Final verification

- [ ] Run the full new-code test surface together:

```bash
./.venv/bin/python -m pytest tests/shell/ tests/cli/test_shell.py -v
```
Expected: all tests pass — `tests/shell/tui/test_printer.py` (4), `test_panels.py` (6), `test_input.py` (7), `test_app.py` (13); `tests/shell/test_bridging.py` (4); `tests/cli/test_shell.py` (3); plus every other pre-existing `tests/shell/` file untouched by this plan — `test_context.py`, `test_resolver.py`, `test_file_filters.py`, `test_plugin_loader.py`, `test_scripts.py`, `test_files.py` — all still passing unchanged.

- [ ] Confirm no stray `cmd2` references remain:

```bash
grep -rn "cmd2" onedep_manager/ tests/ pyproject.toml
```
Expected: no matches.

- [ ] Confirm the full suite's pre-existing failures are unchanged (still the same 7 tests, still failures not new errors):

```bash
./.venv/bin/python -m pytest -q --tb=no 2>&1 | tail -15
```
Expected: `7 failed` (the same 7 `Config()`-needs-a-real-site failures documented in the original shell plan's Global Constraints), 0 collection errors, everything else passing.

- [ ] Run `ruff check` on everything this plan touched:

```bash
~/.local/bin/ruff check onedep_manager tests
```
Expected: no errors. (Use this exact command, over both directories — the original shell plan's final review found that checking only `onedep_manager/shell/` missed unused imports in `tests/`; don't repeat that gap.)

- [ ] Manual smoke test (cannot be automated in a headless sandbox — do this in a real terminal):

```bash
poetry run onedep-manager shell
```
Confirm: the header panel is visible and shows `no entry set` / `no files selected`; typing `entry D_<some id>` updates the panel; `files find` (in a directory with wwPDB-named files, or after `entry`) shows a table and does not touch the panel until `-s` is used, and does touch the selection line when it is; pressing Up/Down in the input recalls prior commands; `!ls` and a bridged command like `paths get archive D_<id>` both flicker to the real terminal and back; `quit` exits cleanly.
