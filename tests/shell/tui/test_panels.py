from pathlib import Path

from onedep_manager.shell.context import ShellContext
from onedep_manager.shell.tui.panels import EntrySelectionPanel, Panel, format_entry_panel


def test_format_entry_panel_with_no_entry_and_no_selection():
    context = ShellContext()

    text = format_entry_panel(context)

    assert "no entry set" in text
    assert "no files selected" in text


def test_format_entry_panel_with_entry_and_no_selection():
    context = ShellContext()
    context.set_entry("D_1000001")

    text = format_entry_panel(context)

    assert "D_1000001" in text
    assert "no files selected" in text


def test_format_entry_panel_lists_selected_filenames():
    context = ShellContext()
    context.set_entry("D_1000001")
    context.set_selection([Path("/a/one.cif"), Path("/a/two.cif")])

    text = format_entry_panel(context)

    assert "one.cif" in text
    assert "two.cif" in text
    assert "more" not in text


def test_format_entry_panel_truncates_past_max_names():
    context = ShellContext()
    context.set_entry("D_1000001")
    context.set_selection([Path(f"/a/file{i}.cif") for i in range(15)])

    text = format_entry_panel(context, max_names=10)

    for i in range(10):
        assert f"file{i}.cif" in text
    for i in range(10, 15):
        assert f"file{i}.cif" not in text
    assert "... 5 more" in text


def test_format_entry_panel_shows_selection_count():
    context = ShellContext()
    context.set_entry("D_1000001")
    context.set_selection([Path("/a/one.cif"), Path("/a/two.cif")])

    text = format_entry_panel(context)

    assert "(2 files)" in text


def test_format_entry_panel_singular_file_count():
    context = ShellContext()
    context.set_selection([Path("/a/one.cif")])

    text = format_entry_panel(context)

    assert "(1 file)" in text


def test_format_entry_panel_styles_labels_bold_cyan_and_values_bright_white():
    context = ShellContext()
    context.set_entry("D_1000001")

    text = format_entry_panel(context)

    styles_by_text = {text.plain[span.start:span.end]: span.style for span in text.spans}
    assert styles_by_text["Entry:      "] == "bold cyan"
    assert styles_by_text["D_1000001"] == "bright_white"
    assert styles_by_text["Selection:  "] == "bold cyan"


def test_entry_selection_panel_is_a_panel():
    panel = EntrySelectionPanel()
    assert isinstance(panel, Panel)


def test_entry_selection_panel_refresh_calls_update_with_formatted_text(monkeypatch):
    panel = EntrySelectionPanel()
    calls = []
    monkeypatch.setattr(panel, "update", lambda content: calls.append(content))
    context = ShellContext()
    context.set_entry("D_1000001")

    panel.refresh_from_context(context)

    assert calls == [format_entry_panel(context)]
