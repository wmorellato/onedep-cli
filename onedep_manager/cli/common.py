import sys
import json
from abc import ABC

from rich import print_json
from rich.console import Console
from rich.table import Table
from rich.theme import Theme


class Printer(ABC):
    def json(self, data: dict):
        raise NotImplementedError()

    def table(self, header: list, data: list):
        raise NotImplementedError()


class RawPrinter(Printer):
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


class ConsolePrinter(Printer):
    def __init__(self, theme=None):
        self.console = Console(theme=Theme(theme))

    def json(self, data: dict):
        print_json(data=data)

    def table(self, header: list, data: list):
        table = Table(show_header=True, header_style="bold blue")

        for col in header:
            table.add_column(col)

        for row in data:
            table.add_row(*row)

        self.console.print(table)
