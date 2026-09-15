import shutil
from pathlib import Path

from onedep_manager.shell.plugin_loader import FilePlugin
from onedep_manager.shell.resolver import UnknownRepositoryError


class CopyPlugin(FilePlugin):
    """`files copy` -- copy the current selection to a plain directory
    (`--dest <path>`) or into a repository for the current entry
    (`--repo <name>`, e.g. `deposit`/`archive`/...)."""

    name = "copy"
    help = "Copy the selection to --dest <path> or --repo <name> (current entry)"

    def run(self, files, context=None, resolver=None, dest=None, repo=None, **kwargs) -> None:
        if not files:
            print("No files selected. Use `files find ... -s` first.")
            return

        if dest and repo:
            print("Usage: files copy --dest <path> | --repo <name> (not both)")
            return

        if repo:
            entry_id = context.current_entry if context else None
            if not entry_id:
                print("files copy --repo: no entry selected. Set one with 'entry <id>' first.")
                return
            try:
                target = resolver.resolve(entry_id, repo)
            except UnknownRepositoryError as exc:
                print(str(exc))
                return
        elif dest:
            target = Path(dest)
        else:
            print("Usage: files copy --dest <path> | --repo <name>")
            return

        target.mkdir(parents=True, exist_ok=True)

        for f in files:
            shutil.copy(f, target)
            print(f"copied {f} -> {target / f.name}")
