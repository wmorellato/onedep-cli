# Embedded Shell (`onedep-manager shell`) — Design

## Problem

Working with OneDep entries and packages today means combining several
things by hand: sourcing `~/.onedep_funcs_<site>` for `cd`/`ls` shortcuts
into entry repositories, and hand-rolling `find`/`md5sum`/`grep` pipelines
to inspect files by wwPDB semantics (content type, milestone, version).
There's no good place to add small ad-hoc tools (copy model files
somewhere, compress a set of files) or to keep a personal library of
scripts without them living loose in `~/bin`.

## Goals

- One interactive surface that combines: navigating entry repositories,
  filtering/inspecting files by wwPDB file-naming semantics, running
  registered scripts, and falling through to a real shell for everything
  else.
- Extensible without re-touching core code: new file actions are
  single-file plugin drop-ins; new scripts are drop-in files with a small
  metadata sidecar.
- Reuses the existing `onedep-manager` command tree (`services`, `tools`,
  `packages`, `instance`, `config`, `paths`) rather than duplicating it.

## Non-goals

- Replacing `onedep-manager paths generate-funcs` — the bash `cd`/`ls`
  functions stay as they are, for people who just want quick navigation
  from their normal shell without launching an interactive session.
- A general-purpose scripting language or query DSL. File filters are a
  fixed set of flags (type, milestone, version, entry/path), not an
  expression language.
- Remote/multi-user shell sessions. This is a local, single-user REPL.

## Approach

Considered aliases/bash functions (today's `generate-funcs`) vs. a real
interactive shell. Bash functions are fine for resolving a path and
`cd`/`ls`-ing into it, but the wwPDB filename semantics needed for file
filtering live in Python (`wwpdb.io.locator.PathInfo` and friends), and a
plugin/script registry with discovery, metadata, and error isolation is
impractical to build in bash. Decision: build `onedep-manager shell` as a
real interactive Python shell.

### REPL foundation: cmd2

Evaluated `cmd2`, `click-shell`, and `prompt_toolkit`:

- `click-shell` would have reused the existing Click command tree with
  near-zero glue code, but is a thinner wrapper (stdlib `cmd`-based
  completion/history) and moves more slowly.
- `prompt_toolkit` gives the best possible UX (used by ipython/pgcli/xonsh)
  but is a low-level toolkit — completion and command dispatch would be
  hand-built, with no reuse of the existing Click tree.
- `python-nubia` was ruled out: archived/unmaintained
  (`facebookarchive/python-nubia`).

**Decision: `cmd2`.** Actively maintained (Production/Stable, monthly
releases), and gives persistent history, tab-completion, command
categories, scripting/macros, and built-in shell delegation (`!<cmd>`) out
of the box. The cost — bridging the existing Click command tree in by
hand rather than getting it for free — is paid once (see below).

## Architecture

New package: `onedep_manager/shell/`

```
onedep_manager/shell/
  app.py          # cmd2.Cmd subclass, registered as `onedep-manager shell`
  context.py      # ShellContext: current entry id, current file selection
  bridging.py     # wraps existing Click groups as cmd2 commands
  files.py        # `files` command set: find/list/hash/info + plugin dispatch
  plugin_loader.py # FilePlugin base class + plugin loader
  scripts.py      # script registry: discovery, tag search, execution
  plugins/         # built-in FilePlugin implementations shipped with this repo
  scripts/         # built-in scripts shipped with this repo (data files, not a Python package)
```

### Command bridging

Each existing Click group (`services`, `tools`, `packages`, `instance`,
`config`, `paths`) is exposed as a cmd2 command by invoking the group's
`main(args, standalone_mode=False, obj=ctx.obj)`, reusing the `CLIContext`
already built for the shell session. This is a mechanical wrapper — no
command logic is duplicated. A command that isn't recognized by cmd2 or
the bridged groups falls through to `cmd2`'s built-in `do_shell`
(`!<cmd>`), running in the user's real shell (cwd, env, aliases intact).

### Navigation / entry context

`ShellContext` holds:
- `current_entry: Optional[str]` — a deposition id, set via `entry
  D_1000001` (validated/resolved the same way `paths get` resolves ids
  today, via `PathInfo`).
- `current_selection: List[Path]` — the most recent set of files marked
  via `files find -s` (see below).

The prompt reflects both, e.g. `(D_1000001) [12 files] onedep>`.

Once an entry is set, repository-scoped commands (`cd deposit`, `cd
archive`, `cd deposit-ui`, `ls upload`, etc.) resolve relative to it —
this is the interactive replacement for the per-repository `cd*`/`ls*`
bash functions in `generate-funcs`. Naming a path type not tied to an
entry (e.g. `cd package <name>`) works the same as it does today via
`ODM_PACKAGE`/`cdpkg`, without requiring an entry context.

### File queries

```
files find [--type T[,T...]] [--milestone M] [--version V] [--entry ID] [-s|--select]
```

- Filters files by wwPDB filename semantics (content type, milestone,
  version) in the given entry's relevant repository, or in the current
  working directory if no entry is given/set.
- **Default behavior: list only.** Renders a table — `ls -l`-style columns
  (permissions, owner, size, mtime) plus an `md5` column — and does not
  change `current_selection`.
- **`-s`/`--select`**: additionally stores the matched files as
  `current_selection`, so a later action can operate on them without
  re-filtering.

```
files list                  # show current_selection, same table format
files hash                  # md5 of current_selection (built-in action)
files info                  # size/mtime of current_selection (built-in action)
files <plugin-name> [args]  # dispatch to a loaded FilePlugin by name
```

Every `files <action>` also accepts the same filter flags directly, as a
one-shot alternative to `find -s` first — e.g. `files hash --type model`
hashes matching files without touching the stored selection.

### Plugins

```python
class FilePlugin(ABC):
    name: str          # invoked as `files <name>`
    help: str

    def run(self, files: list[Path], **kwargs) -> None: ...
```

Loaded at shell startup from two locations, in order:
1. `onedep_manager/shell/plugins/` — built-in plugins shipped with this
   repo (e.g. `copy`, `compress` once written).
2. `~/.onedep/shell/plugins/` — personal/team plugins, no packaging or
   reinstall needed, just drop a `.py` file defining a `FilePlugin`
   subclass.

A plugin that fails to import or raises during discovery is logged as a
warning and skipped — it does not prevent the shell from starting or
other plugins from loading.

### Scripts

`~/.onedep/shell/scripts/` (plus a built-in `onedep_manager/shell/scripts/`
for ones shipped with this repo) holds scripts with a metadata sidecar
(same basename, `.yaml`): `name`, `description`, `tags`. Presence in one
of these directories *is* the trust boundary — nothing outside them can
be run by name, and nothing inside them needs separate approval.

```
scripts list [--tag T]
scripts run <name> [args...]
```

`scripts run` executes the script as a subprocess, streaming
stdout/stderr live and surfacing the real exit code.

### Error handling

- Plugin/script errors are caught at the dispatch boundary and printed as
  shell errors — they never crash the REPL loop.
- An unresolvable entry id, an empty selection for an action that needs
  one, or a script name not found in the registry are all reported as
  clear user-facing errors, not tracebacks.

## Testing

- `ShellContext` state transitions (`entry`, selection set/clear via
  `files find -s`, `files find` without `-s` leaving it untouched).
- Plugin loader: valid plugin loads and is dispatchable by name; a
  plugin that raises on import is skipped with a warning, other plugins
  still load.
- Script registry: tag search, `scripts run` on a registered script
  succeeds, running an unregistered path by name is rejected.
- File-filter logic against wwPDB filenames (type/milestone/version
  matching). The exact API this calls into (`PathInfo` or a sibling in
  `wwpdb.io.locator`) needs confirming against the real package during
  implementation — it isn't installed in this dev environment, so the
  filter logic should be written behind a small seam that can be unit
  tested with fixture filenames independent of the actual wwPDB package.

## Open items for the implementation plan

- Exact wwPDB API for parsing a filename into (content type, milestone,
  version, part) — confirm against `wwpdb.io.locator.PathInfo` (or
  wherever it actually lives) rather than assuming a method name here.
- Table rendering reuses the existing `Printer`/`ConsolePrinter` (rich
  `Table`) from `onedep_manager/cli/common.py`.
- Whether `entry` validation should hard-fail on an unknown id or just
  warn (today's `paths get` hard-fails) — default to matching existing
  behavior unless the plan surfaces a reason not to.
