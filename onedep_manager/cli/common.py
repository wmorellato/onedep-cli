import sys
import json
from abc import ABC

from rich import print_json
from rich.table import Table


class Printer(ABC):
    def json(self, data: dict):
        raise NotImplementedError()

    def table(self, header: list, data: list):
        raise NotImplementedError()
    
    def info(self, message):
        raise NotImplementedError()
    
    def error(self, message):
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
    def __init__(self, console):
        self.console = console

    def json(self, data: dict):
        print_json(data=data)

    def table(self, header: list, data: list):
        table = Table(show_header=True, header_style="bold blue")

        for col in header:
            table.add_column(col)

        for row in data:
            table.add_row(*row)

        self.console.print(table)

    # need to find a way to define these styles in a central place
    # and allow overrides
    def info(self, message):
        self.console.print(f"[dark_sea_green4]●[/dark_sea_green4] {message}")

    def error(self, message):
        self.console.print(f"[indian_red]●[/indian_red] {message}")
