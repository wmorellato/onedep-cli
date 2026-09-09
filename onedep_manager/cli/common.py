import sys
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from rich import print_json
from rich.table import Table

from onedep_manager.config import Config


@dataclass
class CLIContext:
    config: Config


def get_config(ctx) -> Config:
    """Return the shared Config from the root CLI context.

    Falls back to constructing a fresh Config() when a command is invoked
    directly without going through the root `cli()` group (e.g. tests that
    invoke a leaf command via CliRunner without setting `obj=`), so this is
    backward compatible with call sites that don't go through the full CLI.
    """
    if ctx.obj is not None:
        return ctx.obj.config
    return Config()


class Printer(ABC):
    @abstractmethod
    def json(self, data: dict):
        raise NotImplementedError()

    @abstractmethod
    def table(self, header: list, data: list):
        raise NotImplementedError()

    @abstractmethod
    def info(self, message):
        raise NotImplementedError()

    @abstractmethod
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

    def info(self, message):
        self._stream.write(f"{message}\n")
        self._stream.flush()

    def error(self, message):
        self._stream.write(f"{message}\n")
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
        self.console.print(f"[slate_blue3]⬢[/slate_blue3] {message}")

    def error(self, message):
        self.console.print(f"[indian_red]⬢[/indian_red] {message}")
