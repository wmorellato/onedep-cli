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
