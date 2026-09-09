from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ShellContext:
    """Mutable session state for one running `onedep-manager shell` instance."""

    current_entry: Optional[str] = None
    current_selection: List[Path] = field(default_factory=list)

    def set_entry(self, entry_id: str) -> None:
        self.current_entry = entry_id
        self.current_selection = []

    def set_selection(self, files: List[Path]) -> None:
        self.current_selection = list(files)

    def clear_selection(self) -> None:
        self.current_selection = []
