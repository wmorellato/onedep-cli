from rich.table import Table
from rich.text import Text

from onedep_manager.shell.tui.printer import TextualPrinter


class FakeLog:
    def __init__(self):
        self.written = []

    def write(self, content):
        self.written.append(content)


def test_info_writes_styled_text():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.info("hello")

    assert len(log.written) == 1
    written = log.written[0]
    assert isinstance(written, Text)
    assert written.plain == "⬢ hello"
    assert written.style == "slate_blue3"


def test_error_writes_styled_text():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.error("something broke")

    written = log.written[0]
    assert isinstance(written, Text)
    assert written.plain == "⬢ something broke"
    assert written.style == "indian_red"


def test_table_writes_a_rich_table_with_header_and_rows():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.table(["a", "b"], [["1", "2"], ["3", "4"]])

    assert len(log.written) == 1
    written = log.written[0]
    assert isinstance(written, Table)
    assert [col.header for col in written.columns] == ["a", "b"]
    assert written.row_count == 2


def test_json_writes_a_json_renderable():
    log = FakeLog()
    printer = TextualPrinter(log)

    printer.json({"foo": "bar"})

    assert len(log.written) == 1
    # rich.json.JSON renders from the data it was built with; just confirm
    # the right type reached the log, formatting is rich's own concern.
    from rich.json import JSON

    assert isinstance(log.written[0], JSON)
