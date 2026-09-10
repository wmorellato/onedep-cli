from rich.text import Text
from textual.widgets import Static

from onedep_manager.shell.context import ShellContext

_LABEL_WIDTH = 12
_LABEL_STYLE = "bold cyan"
_VALUE_STYLE = "bright_white"


def format_entry_panel(context: ShellContext, max_names: int = 10) -> Text:
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
        count = len(selection)
        selection_text += f" ({count} file{'s' if count != 1 else ''})"

    text = Text()
    text.append(f"{'Entry:':<{_LABEL_WIDTH}}", style=_LABEL_STYLE)
    text.append(entry, style=_VALUE_STYLE)
    text.append("\n")
    text.append(f"{'Selection:':<{_LABEL_WIDTH}}", style=_LABEL_STYLE)
    text.append(selection_text, style=_VALUE_STYLE)
    return text


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
