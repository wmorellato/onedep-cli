from io import StringIO

from onedep_manager.cli.common import Printer


def test_printer_json():
    """Test the printer function."""
    stream = StringIO()
    p = Printer(stream=stream)
    p.json({"foo": "bar"})

    assert stream.getvalue() == '{\n  "foo": "bar"\n}'


def test_printer_table():
    """Test the printer function."""
    stream = StringIO()
    p = Printer(stream=stream)
    p.table([["foo", "bar"], ["baz", "qux"]])

    assert stream.getvalue() == "foo  bar\nbaz  qux\n"
