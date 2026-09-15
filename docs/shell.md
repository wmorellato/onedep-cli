# `onedep-manager shell`

An interactive shell for navigating entries, inspecting files, running
whitelisted scripts, and extending file actions with drop-in plugins —
without leaving a single session. Built on
[Textual](https://textual.textualize.io/).

## Launching

```bash
poetry run onedep-manager shell
poetry run onedep-manager shell --site WWPDB_DEPLOY_TEST_RU   # -i works too
```

The screen has three parts:
- a **header panel** at the top, always visible, showing the current
  working directory, the current entry, and the file selection
  (filenames, truncated with `... N more` past 10, with a total file
  count)
- a **scrolling log** in the middle, where command output appears
- a **command line** at the bottom, where you type

```
╭───────────────────────────────────────────────────────────╮
│ Directory:  ~/data/archive/D_800000                        │
│ Entry:      D_800000                                       │
│ Selection:  D_800000_model_P1.cif.V1, ... 3 more (4 files) │
╰───────────────────────────────────────────────────────────╯
 (command output scrolls here)


 command...
```

Exit by typing `quit` or `exit` and pressing Enter, or press `Ctrl+Q`.
Type `help` to list every available command, including any loaded
plugins and bridged command groups.

## Existing commands work as-is

`services`, `tools`, `packages`, `instance`, `config`, and `paths` — the
same command groups available from `onedep-manager <group> ...` — are all
usable directly inside the shell:

```
> services status
> paths get archive D_800000
```

Running one of these (or a `!<command>` shell escape, below, or `scripts
run`) captures whatever it prints and writes it straight into the log —
there's no separate terminal screen or flicker, and nothing to wait for.
**Trade-off:** because there's no real terminal handed over, anything
that needs one to work — an editor (`!vim file.txt`), an interactive
session (`!ssh host`), or a bridged command that prompts you for
confirmation — will not work through the shell. Colors are usually lost
too, since most tools auto-detect that they're not writing to a real
terminal and disable them on their own (the same way `ls | cat` looks
different from plain `ls`); if a tool forces color anyway, the shell
still renders it correctly.

If one of these groups can't be imported in your environment (e.g. a
missing dependency), the shell reports it in the log and starts anyway
with the other groups available — one broken group never blocks the rest.

Anything the shell doesn't recognize as a command or a bridged group name
is reported as an unknown command — it does not fall through to a real
shell. For that, use `!`:

```
> !ls -la
> !git status
```

## Command history

Press Up/Down to recall previously entered commands.

## Entry navigation

```
entry D_800000      # set the current entry
entry               # show the current entry (or "No entry set")
```

Setting a new entry clears the current file selection. The shell resolves
the entry's archive path immediately and reports it in the log (without
refusing to set the entry) if that path doesn't exist yet:

```
> entry D_9999999
Entry 'D_9999999' resolved to '/data/archive/D_9999999', which does not exist
```

## Changing directory between repositories

```
cd <repo> [identifier]
```

Resolves `<repo>` + `identifier` to a filesystem path, `os.chdir`s the
shell process into it, and sets it as the current entry (same as running
`entry <identifier>`) — so a subsequent `files find` with no `--entry`
picks it up, and the header panel's directory/entry rows update.
`identifier` can be omitted if an entry is already set. `<repo>` accepts:
`tempdep`, `deposit`, `deposit-ui`, `archive`, `upload`, `pickles`,
`session`.

Short mnemonics do the same thing for one repo each, mirroring the `cd*`
bash functions from `onedep-manager paths generate-funcs`:

```
cdt [id]     # tempdep
cdd [id]     # deposit
cdui [id]    # deposit-ui
cda [id]     # archive
cds [id]     # session
cdup [id]    # upload
cdpkl [id]   # pickles
```

```
> cdd D_800000
> cda
```

`cdwfi` navigates into a workflow instance directory — `cdwfi <wfinst_id>`
uses the current entry, or `cdwfi <entry_id> <wfinst_id>` for an explicit
one. A repo/directory that doesn't exist reports a clean error instead of
changing directory.

There's no `cd`-style command for `ccid`, `wfxml`, or `package` (the
bash `viccid`/`viwfx`/`cdpkg` functions) — those stay bash-only for now.

## Finding and acting on files

```
files find [--type T[,T...]] [--milestone M] [--version V|latest]
           [--entry ID] [--repo REPO] [-s|--select]
files list
files hash
files info
```

`files find` lists matching files as a table — permissions, owner, size,
mtime, md5, and path, `ls -l`-style — without touching your current
selection, unless you pass `-s`/`--select`, which stores the matches as
the selection for later commands to reuse (and updates the header panel).

**Where it looks:** with an entry — either `--entry ID` or one already set
via `entry` — it resolves that entry's repository directory (`archive` by
default, or `deposit`/`deposit-ui`/`tempdep`/`upload`/`pickles` via
`--repo`) and lists files there. With no entry at all, it lists your
current working directory (`--repo` has nothing to apply to in that case).
With no entry context and no filters of any kind, `files
find`/`list`/`hash`/`info` show whatever's currently selected instead.

**Filters:**
- `--type model` or `--type model,model-upload` — exact content-type match
  (wwPDB's `D_########_<type>_P#.<fmt>.V#` naming convention)
- `--milestone upload` — matches a `-upload` suffix on the content type
  (`model-upload`, `sf-upload`, ...)
- `--version 3` or `--version latest` — an exact version, or the highest
  version per (dataset, type, part, format) group

```
> files find --type model
┏━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ permissions ┃ owner ┃ size ┃ mtime             ┃ md5                            ┃ path                         ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ -rw-r--r--  │ user  │ 1234 │ 2026-09-09 10:00  │ 5d41402abc4b2a76b9719d911017c…│ .../D_800000_model_P1.cif.V1 │
└─────────────┴───────┴──────┴───────────────────┴────────────────────────────────┴──────────────────────────────┘

> files find --type model -s
> files hash
```

`hash`/`info`/`list` accept the same filter flags for a one-shot query
(`files hash --type sf` hashes matching files without touching your
stored selection); called with no flags, they operate on the current
selection instead. **Note:** in this version, `find`/`list`/`hash`/`info`
all render the identical table — `hash` and `info` don't yet show a
narrower column set. A bad `--version` value or an unknown `--repo` reports
a clean error rather than a crash.

`ls` and `ff` are shorthand aliases for `files list` and `files find` —
`ls --type model` is exactly `files list --type model`. Note `ls` shadows
a plain OS directory listing; use `!ls` for that instead.

### Built-in plugins

**`copy`** — copy the current selection to a plain directory, or into a
repository for the current entry:

```
> files copy --dest /tmp/out
copied /data/archive/D_800000/D_800000_model_P1.cif.V1 -> /tmp/out/D_800000_model_P1.cif.V1

> files copy --repo deposit
copied /data/archive/D_800000/D_800000_model_P1.cif.V1 -> /data/deposit/D_800000/D_800000_model_P1.cif.V1
```

`--dest <path>` copies into an arbitrary directory, creating it if it
doesn't exist. `--repo <name>` resolves that repository's path for the
*current entry* (same repos as `cd`/`files find --repo`) and copies
there instead — `--dest` and `--repo` are mutually exclusive, and `--repo`
requires an entry to be selected first (see `entry`/`cd`). Either way, a
missing selection, an unknown repo, or a copy failure reports a clean
error instead of crashing.

### Extending `files` with plugins

Any `.py` file dropped into a plugin directory that defines a `FilePlugin`
subclass becomes a new `files <name>` action — no core code changes:

```python
# ~/.onedep/shell/plugins/touch_marker.py
from onedep_manager.shell.plugin_loader import FilePlugin

class TouchMarkerPlugin(FilePlugin):
    name = "touch-marker"
    help = "Create a .done marker next to the current entry's archive dir"

    def run(self, files, context=None, resolver=None, **kwargs):
        if not context or not context.current_entry:
            print("Usage: files touch-marker (requires a current entry)")
            return
        archive_dir = resolver.resolve(context.current_entry, "archive")
        (archive_dir / ".done").touch()
        print(f"marked {archive_dir}")
```

```
> files touch-marker
marked /data/archive/D_800000
```

A plugin's `print()` output appears in the log, same as any other
command's output. Trailing `--key value` / `--flag` tokens after the
plugin name are parsed into keyword arguments (`--dest /tmp` →
`dest="/tmp"`, `--verbose` → `verbose=True`). `run` always also receives
`context` (the shell's `ShellContext` — current entry/selection) and
`resolver` (its `EntryPathResolver`) as keyword arguments alongside the
current selection, so a plugin can act relative to whatever's currently
selected without the user retyping it; a plugin that doesn't need them
can just declare `**kwargs`. A plugin that raises reports a clean error
instead of crashing the shell. Running `files` with no arguments lists
usage and, if any plugins are loaded, their names.

Plugins are scanned from two places, in order (a later one overrides an
earlier plugin of the same `name`):
1. `onedep_manager/shell/plugins/` — shipped with this repo (this is
   where `copy` itself lives)
2. `~/.onedep/shell/plugins/` — yours, personal or team, no packaging or
   reinstall needed

A plugin file that fails to import, or a plugin class that fails to
construct, is logged as a warning and skipped — it never stops the shell
from starting or other plugins from loading.

## Scripts

```
scripts list [--tag T]
scripts run <name> [args...]
```

A script is runnable by name only if it's whitelisted **by location**: it
lives in one of the script directories *and* has a matching metadata
sidecar next to it. Presence elsewhere, or presence without a sidecar,
means the shell can't see it — that's the whole trust boundary.

```
~/.onedep/shell/scripts/
  hash_models.sh
  hash_models.sh.yaml
```

```yaml
# hash_models.sh.yaml
name: hash_models.sh
description: md5sum every model file in the current directory
tags: [models, hashing]
```

```
> scripts list --tag models
hash_models.sh    models, hashing    md5sum every model file in the current directory
> scripts run hash_models.sh
```

`scripts run` runs the script the same way bridged commands do — its
output is captured and written into the log, and a non-zero exit code is
reported as an error afterward. As with plugins, these directories are
scanned in order (built-in, then `~/.onedep/shell/scripts/`), and a
script that can't be executed (missing +x bit, etc.) reports a clean
error rather than a traceback.

## Known limitations (current version)

- **No real interactive terminal for external commands.** `!<command>`,
  bridged commands, and `scripts run` all capture output rather than
  handing over a real terminal — see "Existing commands work as-is"
  above. An editor, an SSH session, or a confirmation prompt won't work.
- **No tab-completion.** This is an accepted trade-off of moving off
  `cmd2`/readline, not a bug — command entry is plain typing plus Up/Down
  history recall.
- **No shell equivalent of `viccid`/`viwfx`/`cdpkg`.** Those bash functions
  (open a CCD/wfxml file in `$EDITOR`, cd into a package repo by name) are
  still bash-only for now.
- `files hash`/`files info` currently render the same full table as
  `files list`/`files find` — there's no narrower, action-specific column
  set yet.
- Every `files` listing computes an md5 for every matched file, even for
  `files info`. On a directory of large files this can be slow; there's no
  way to list without paying that cost yet.
- `entry <id>` only reports a problem in the log if the resolved archive
  path doesn't exist — it never refuses to set the entry.
