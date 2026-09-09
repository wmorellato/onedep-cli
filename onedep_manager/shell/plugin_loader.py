import importlib.util
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class FilePlugin(ABC):
    """Base class for a `files <name>` action plugin.

    Subclasses set `name` (the action name used to invoke it) and `help`
    (shown in `files` usage output), and implement `run`.
    """

    name: str
    help: str = ""

    @abstractmethod
    def run(self, files: list, **kwargs) -> None:
        raise NotImplementedError()


def _load_module(py_file: Path):
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins(directories: List[Path]) -> Dict[str, FilePlugin]:
    """Scan `directories` in order for FilePlugin subclasses.

    A plugin file that fails to import, or a plugin class that fails to
    instantiate, is logged as a warning and skipped -- it never prevents
    the shell from starting or other plugins from loading. Directories
    are scanned in the order given, so a later directory's plugin with
    the same `name` overrides an earlier one (built-ins first, then the
    user's personal directory).
    """
    plugins: Dict[str, FilePlugin] = {}

    for directory in directories:
        if not directory.is_dir():
            continue

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            try:
                module = _load_module(py_file)
            except Exception:
                logger.warning("Failed to load plugin file '%s'", py_file, exc_info=True)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is FilePlugin or not issubclass(obj, FilePlugin):
                    continue

                try:
                    instance = obj()
                except Exception:
                    logger.warning("Failed to instantiate plugin class '%s' from '%s'", obj.__name__, py_file, exc_info=True)
                    continue

                plugins[instance.name] = instance

    return plugins
