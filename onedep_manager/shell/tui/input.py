from typing import List, Optional

from textual.binding import Binding
from textual.widgets import Input


class HistoryInput(Input):
    """An Input with up/down command history recall."""

    BINDINGS = [
        Binding("up", "history_prev", "Previous command", show=False),
        Binding("down", "history_next", "Next command", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history: List[str] = []
        self._history_index: Optional[int] = None

    def add_to_history(self, command: str) -> None:
        command = command.strip()
        if command and (not self._history or self._history[-1] != command):
            self._history.append(command)
        self._history_index = None

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._history_index is None:
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        self.value = self._history[self._history_index]

    def action_history_next(self) -> None:
        if self._history_index is None:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.value = self._history[self._history_index]
        else:
            self._history_index = None
            self.value = ""
