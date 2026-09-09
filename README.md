# onedep-cli

Proposal for a OneDep command line tool. Description is done [this specification](https://wmorellato.github.io/brandon/specification/spec/) and the application stub will be built using Brandon.

## Install

This project uses [Poetry](https://python-poetry.org/).

```bash
poetry install --with dev
```

`onedep_manager` also depends on internal wwPDB packages (`wwpdb.utils.config`, `wwpdb.io`, ...) that are not
published to public PyPI and are not declared in `pyproject.toml`. They need to be available in your environment
some other way (a private index, an editable install from a local checkout, a pre-built environment) before the
commands below will run.

## Usage

```bash
poetry run onedep-manager --help
```

Command groups: `packages`, `services`, `instance`, `config`, `paths`, `tools`. Run `onedep-manager <group> --help`
for the commands in each group.

### Interactive shell

```bash
poetry run onedep-manager shell
```

An interactive `cmd2`-based shell wrapping all of the above, plus entry
navigation, wwPDB-aware file queries, drop-in file-action plugins, and a
whitelisted script registry. See [`docs/shell.md`](docs/shell.md).

## Tests

```bash
poetry run pytest
poetry run ruff check onedep_manager tests
```
