from io import StringIO

from onedep_manager.cli.common import RawPrinter


def test_printer_json():
    """Test the printer function."""
    stream = StringIO()
    p = RawPrinter(stream=stream)
    p.json({"foo": "bar"})

    assert stream.getvalue() == '{\n  "foo": "bar"\n}'


def test_printer_table():
    """Test the printer function."""
    stream = StringIO()
    p = RawPrinter(stream=stream)
    p.table(header=["foo", "bar"], data=[["baz", "qux"]])

    assert stream.getvalue() == "foo  bar\nbaz  qux\n"
