# `onedep-manager shell`

An interactive shell for navigating entries, inspecting files, running
whitelisted scripts, and extending file actions with drop-in plugins —
without leaving a single session. Built on [`cmd2`](https://cmd2.readthedocs.io/).

## Launching

```bash
poetry run onedep-manager shell
poetry run onedep-manager shell --site WWPDB_DEPLOY_TEST_RU   # -i works too
```

The prompt shows the current entry and selection size:

```
(-) [0 files] onedep>
```

Exit with `quit`, `exit`, or Ctrl-D (all provided by `cmd2`).

## Existing commands work as-is

`services`, `tools`, `packages`, `instance`, `config`, and `paths` — the
same command groups available from `onedep-manager <group> ...` — are all
usable directly inside the shell:

```
(-) [0 files] onedep> services status
(-) [0 files] onedep> paths get archive D_800000
```

If one of these groups can't be imported in your environment (e.g. a
missing dependency), the shell prints a warning and starts anyway with the
other groups available — one broken group never blocks the rest.

Anything the shell doesn't recognize falls through to your real shell,
same as typing `!<command>` in any `cmd2` app:

```
(-) [0 files] onedep> !ls -la
(-) [0 files] onedep> !git status
```

## Entry navigation

```
entry D_800000      # set the current entry
entry               # show the current entry (or "No entry set")
```

Setting a new entry clears the current file selection. The shell resolves
the entry's archive path immediately and warns (without refusing to set
it) if that path doesn't exist yet:

```
(-) [0 files] onedep> entry D_9999999
Warning: Entry 'D_9999999' resolved to '/data/archive/D_9999999', which does not exist
(D_9999999) [0 files] onedep>
```

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
the selection for later commands to reuse.

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
(D_800000) [0 files] onedep> files find --type model
┏━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ permissions ┃ owner ┃ size ┃ mtime             ┃ md5                            ┃ path                         ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ -rw-r--r--  │ user  │ 1234 │ 2026-09-09 10:00  │ 5d41402abc4b2a76b9719d911017c…│ .../D_800000_model_P1.cif.V1 │
└─────────────┴───────┴──────┴───────────────────┴────────────────────────────────┴──────────────────────────────┘

(D_800000) [0 files] onedep> files find --type model -s
(D_800000) [1 files] onedep> files hash
```

`hash`/`info`/`list` accept the same filter flags for a one-shot query
(`files hash --type sf` hashes matching files without touching your
stored selection); called with no flags, they operate on the current
selection instead. **Note:** in this version, `find`/`list`/`hash`/`info`
all render the identical table — `hash` and `info` don't yet show a
narrower column set. A bad `--version` value or an unknown `--repo` reports
a clean error rather than a crash.

### Extending `files` with plugins

Any `.py` file dropped into a plugin directory that defines a `FilePlugin`
subclass becomes a new `files <name>` action — no core code changes:

```python
# ~/.onedep/shell/plugins/copy_to.py
from onedep_manager.shell.plugin_loader import FilePlugin
import shutil

class CopyToPlugin(FilePlugin):
    name = "copy-to"
    help = "Copy the current selection to --dest"

    def run(self, files, **kwargs):
        dest = kwargs.get("dest")
        if not dest:
            print("Usage: files copy-to --dest <path>")
            return
        for f in files:
            shutil.copy(f, dest)
            print(f"copied {f} -> {dest}")
```

```
(D_800000) [1 files] onedep> files copy-to --dest /tmp/out
```

Trailing `--key value` / `--flag` tokens after the plugin name are parsed
into keyword arguments (`--dest /tmp` → `dest="/tmp"`, `--verbose` →
`verbose=True`) and passed to `run(files, **kwargs)` alongside the current
selection. A plugin that raises reports a clean error instead of crashing
the shell. Running `files` with no arguments lists usage and, if any
plugins are loaded, their names.

Plugins are scanned from two places, in order (a later one overrides an
earlier plugin of the same `name`):
1. `onedep_manager/shell/plugins/` — shipped with this repo
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
(-) [0 files] onedep> scripts list --tag models
hash_models.sh    models, hashing    md5sum every model file in the current directory
(-) [0 files] onedep> scripts run hash_models.sh
```

`scripts run` executes the script as a real subprocess — output streams
live, and a non-zero exit code is reported as an error. As with plugins,
these directories are scanned in order (built-in, then
`~/.onedep/shell/scripts/`), and a script that can't be executed (missing
+x bit, etc.) reports a clean error rather than a traceback.

## Known limitations (current version)

- **No `cd`/`ls` between repositories yet.** Setting an entry with `entry`
  and querying files with `files find --repo <name>` works; interactively
  changing your actual working directory into `deposit`/`archive`/etc. the
  way the bash functions from `onedep-manager paths generate-funcs` do is
  not implemented. Those bash functions are still the way to do that today.
- `files hash`/`files info` currently render the same full table as
  `files list`/`files find` — there's no narrower, action-specific column
  set yet.
- Every `files` listing computes an md5 for every matched file, even for
  `files info`. On a directory of large files this can be slow; there's no
  way to list without paying that cost yet.
- `entry <id>` only warns (via `pwarning`) if the resolved archive path
  doesn't exist — it never refuses to set the entry.
