import pytest
from textual.app import App, ComposeResult

from onedep_manager.shell.tui.input import HistoryInput


class _HistoryInputTestApp(App):
    def compose(self) -> ComposeResult:
        yield HistoryInput(id="cmdline")


@pytest.mark.asyncio
async def test_up_recalls_most_recent_command():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")

        assert input_widget.value == "entry D_1000001"


@pytest.mark.asyncio
async def test_up_up_recalls_further_back():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")
        await pilot.press("up")

        assert input_widget.value == "files find"


@pytest.mark.asyncio
async def test_up_past_the_oldest_entry_stays_on_oldest():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")

        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("up")

        assert input_widget.value == "files find"


@pytest.mark.asyncio
async def test_down_after_up_returns_toward_empty():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)
        input_widget.add_to_history("files find")
        input_widget.add_to_history("entry D_1000001")

        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("down")
        await pilot.press("down")

        assert input_widget.value == ""


@pytest.mark.asyncio
async def test_up_with_no_history_does_nothing():
    app = _HistoryInputTestApp()
    async with app.run_test() as pilot:
        input_widget = app.query_one("#cmdline", HistoryInput)

        await pilot.press("up")

        assert input_widget.value == ""


def test_add_to_history_skips_consecutive_duplicates():
    input_widget = HistoryInput.__new__(HistoryInput)
    input_widget._history = []
    input_widget._history_index = None

    input_widget.add_to_history("files find")
    input_widget.add_to_history("files find")

    assert input_widget._history == ["files find"]


def test_add_to_history_ignores_empty_command():
    input_widget = HistoryInput.__new__(HistoryInput)
    input_widget._history = []
    input_widget._history_index = None

    input_widget.add_to_history("")

    assert input_widget._history == []
