# Shell TUI Redesign — Design

## Problem

The current `onedep-manager shell` (built on `cmd2`) is a scrolling
line-based REPL: every command's output just prints and scrolls away.
There's no way to keep the current entry and file selection visible while
working — you have to re-run `entry`/`files list` to remind yourself what
context you're in. `cmd2` can't provide a persistent fixed panel: it's
built on GNU readline, which owns exactly one line of the terminal for
input editing and has no concept of a separate, independently-refreshed
screen region. Bolting a fixed status line on top via ANSI cursor tricks
was evaluated and rejected as fragile (breaks across terminal emulators,
on resize, and fights readline for cursor ownership).

## Goals

- A fixed header panel, always visible, showing the current entry and the
  current file selection (truncated past a threshold, e.g. `... 7 more`).
- Design the header as a container of independent panels, not one
  hardcoded block, so a second panel can be added later without
  restructuring anything.
- Preserve every existing command and its behavior exactly
  (`entry`, `files find/list/hash/info`, `scripts list/run`, plugin
  dispatch, the bridged `services`/`tools`/`packages`/`instance`/`config`/
  `paths` groups, and `!<cmd>` shell delegation).

## Non-goals

- Mouse support, clickable file selection, or additional interactive
  widgets beyond the header panel and a scrolling output log — explicitly
  out of scope for this redesign (confirmed with the user: like-for-like
  behavior, one new panel, room for more panels *later*, not now).
- A fallback mode for non-interactive/non-tty use. `onedep-manager shell`
  is launched interactively by a person at a terminal; no scripted or CI
  usage exists today. Accepting a hard real-terminal requirement removes
  an entire second code path.
- Preserving `cmd2`'s specific history/tab-completion implementation.
  Textual's `Input` widget has its own history behavior; matching `cmd2`'s
  exactly is not a goal, only "the shell remains usable," to be confirmed
  during planning.

## Approach

Evaluated three options:

- **Rejected: stay on `cmd2`, fake a fixed line with Rich `Live` +
  ANSI cursor tricks.** `cmd2`'s blocking readline input call doesn't hand
  control back between keystrokes, so an independent redraw loop and
  readline fight over the terminal. Fragile across terminal emulators and
  on resize; already ruled out in the prior conversation before this spec.
- **Rejected: hand-roll on `prompt_toolkit`'s low-level `Application`/
  `Layout`.** Same general shape as the recommended option below, but
  `prompt_toolkit` has no `RichLog`-equivalent scrolling-output widget and
  no `suspend()`-equivalent helper for handing the terminal to a
  subprocess — both would need to be built from scratch for no benefit
  over Textual, which ships both.
- **Chosen: rebuild the shell's presentation layer on
  [Textual](https://textual.textualize.io/).** Verified empirically
  (not just from documentation) during brainstorming:
  - Textual's current release requires `rich>=14.2.0`, which conflicts
    with this project's `rich = "^13.0"` pin. Textual `3.0.0` (through at
    least `0.60.0`) requires only `rich>=13.3.3`, which **is** compatible
    — confirmed via `pip download` + reading the wheel's `METADATA`, the
    same way the `cmd2` pin was verified in the original shell plan.
  - Textual requires Python `>=3.9,<4.0` — already satisfied by this
    project's floor (bumped to `^3.9` for `cmd2` in the original plan).
  - `App.suspend()` — a context manager built specifically for handing
    the whole terminal to a subprocess (e.g. launching `vim`) and
    resuming afterward — exists in Textual `3.0.0`, confirmed by
    `'suspend' in dir(App)` in an installed `3.0.0` environment.
  - `RichLog` (a scrollable, appendable output widget) and `reactive`
    attributes both exist in `3.0.0`, confirmed by direct import.

  **Exact version pin** (e.g. `^3.0` vs. a later 13.x-rich-compatible
  release) is an implementation-planning decision, not a design one —
  deferred to the plan, same as `cmd2`'s exact pin was.

## Architecture

New subpackage: `onedep_manager/shell/tui/`

```
onedep_manager/shell/tui/
  app.py       # OneDepTuiApp(textual.app.App) -- replaces OneDepShell(cmd2.Cmd)
  panels.py    # Panel base widget + EntrySelectionPanel
  printer.py   # TextualPrinter(Printer), writes into the RichLog
onedep_manager/cli/shell.py            # modified: launch OneDepTuiApp instead
pyproject.toml                          # modified: drop cmd2, add textual
```

Everything else under `onedep_manager/shell/` — `context.py`,
`resolver.py`, `file_filters.py`, `plugin_loader.py`, `scripts.py`,
`files.py` (the `FilesCommands` mixin), and `bridging.py`'s actual
Click-invocation call — is untouched. This is possible because the
original shell design already fully decoupled that logic from `cmd2`:
`FilesCommands` only ever depended on `self.context`/`self.resolver`/
`self.plugins`/`self.printer` as a documented attribute contract, never
on anything `cmd2`-specific. `cmd2` is dropped as a dependency once this
lands (`onedep_manager/shell/app.py`, the old `OneDepShell(cmd2.Cmd)`,
is deleted, along with `tests/shell/test_app.py`'s `cmd2`-specific
assertions — replaced by `tui/`'s own tests).

`bridging.py`'s `bridge_click_group()` (which does `setattr(shell,
f"do_{group.name}", handler)`, a `cmd2`-specific registration pattern)
is replaced by a small equivalent that the new app calls directly per
bridged group name — the `group.main(args=..., prog_name=..., obj=...,
standalone_mode=False)` call itself, and its `ClickException`/`SystemExit`
handling, carry over verbatim.

## Components

### Panel system

The header is a `Vertical` container holding a list of independent
`Panel` widgets — not one hardcoded block of text — so a second panel
later is just a new `Panel` subclass appended to that container, no
registry or plugin mechanism needed for something that today has exactly
one instance.

```python
class Panel(Static):
    def refresh_from_context(self, context: ShellContext) -> None: ...
```

`EntrySelectionPanel` shows the current entry (or a placeholder like
`no entry set`) and the current selection as a list of filenames,
truncated past 10 with `... N more`. The App calls `refresh_from_context`
on every panel after each command completes — not a Textual-reactive
watcher on `ShellContext` itself, since `ShellContext` is a plain
dataclass mutated by existing, unchanged code, not a reactive object.
Re-rendering after every command is cheap and simple; wiring reactivity
into `ShellContext` would mean changing code this redesign is supposed to
leave alone.

### Output: `TextualPrinter`

Implements the existing `Printer` ABC (`onedep_manager/cli/common.py`),
writing formatted output into the body `RichLog` instead of a `rich.
Console`. Every existing consumer (`FilesCommands`, `ScriptRegistry`
error paths, `do_entry`/`do_scripts`-equivalent handlers) depends only on
`Printer`, so none of them change.

### Input and dispatch

A bottom `Input` widget takes typed commands. On submit, the App parses
the line (`shlex.split`, matching today's behavior) and routes to the
same logic already in `FilesCommands.dispatch` and the `entry`/`scripts`
handlers — moved from `cmd2` `do_*` methods onto plain methods on the new
App class, calling the identical underlying code.

### Shell and bridged-command delegation

Both `!<cmd>` and the bridged Click groups run inside `with self.
suspend(): ...`, using the exact `group.main(...)` call `bridging.py`
already makes today. The terminal briefly reverts to normal (a visible
flicker: screen clears, the command's own output prints normally, then
Textual redraws) — this is the deliberate, accepted cost of preserving
those commands' actual output exactly as today rather than capturing and
re-rendering it inside the TUI, which risks corrupting `Rich`'s own
width/color detection when it can't see the real terminal.

## Testing

Textual ships `App.run_test()`, an async context manager (a "Pilot")
that drives the app without a real terminal — simulating keypresses,
reading the rendered widget tree — replacing `capsys`/`capfd`-based
assertions for anything in `tui/`. Tests for `context.py`, `resolver.py`,
`files.py`, etc. are unaffected and stay exactly as they are.

## Open items for the implementation plan

- Exact Textual version pin (a specific `rich>=13.3.3`-compatible release,
  not necessarily `3.0.0` itself — verify what's current within that
  compatible band before committing to one, the same way `cmd2`'s pin was
  finalized during planning, not brainstorming).
- Exact `run_test()`/Pilot API shape for the version pinned, and whether
  `Input`'s built-in history is sufficient or needs any extra wiring —
  confirm against the actual installed package, not documentation alone.
- Whether `bridging.py` needs a new function or whether the existing
  `bridge_click_group()` can be adapted in place (it currently mutates a
  `cmd2`-shaped object via `setattr`, which no longer applies).
- Confirm `RichLog`'s exact write API (`write()` accepting a string vs. a
  Rich renderable) matches what `TextualPrinter` needs to hand it.
