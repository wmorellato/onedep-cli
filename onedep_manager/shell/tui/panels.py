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
