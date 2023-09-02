import sys
import json

from rich.console import Console
from rich.table import Table


class Printer:
    def __init__(self, stream=None):
        self._stream = stream or sys.stdout
    
    def json(self, data: dict):
        self._stream.write(json.dumps(data, indent=2))
        self._stream.flush()
    
    def table(self, header: list, data: list):
        self._stream.write("  ".join(header))
        self._stream.write("\n")

        for row in data:
            self._stream.write("  ".join(row))
            self._stream.write("\n")

        self._stream.flush()

    def rich_table(self, header: list, data: list):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        for col in header:
            table.add_column(col)

        for row in data:
            table.add_row(*row)

        console.print(table)
