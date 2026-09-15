import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ScriptNotFoundError(Exception):
    """Raised when ScriptRegistry.run() is asked for a script that isn't registered."""


@dataclass
class ScriptMetadata:
    name: str
    path: Path
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ScriptResult:
    returncode: int
    stdout: str
    stderr: str


class ScriptRegistry:
    """Discovers whitelisted scripts: presence in one of `directories`, with
    a matching `<script>.yaml` metadata sidecar, is what makes a script
    runnable by name. Nothing outside these directories can be run.
    """

    def __init__(self, directories: List[Path]):
        self._scripts: Dict[str, ScriptMetadata] = {}
        self._discover(directories)

    def _discover(self, directories: List[Path]) -> None:
        for directory in directories:
            if not directory.is_dir():
                continue

            for sidecar in sorted(directory.glob("*.yaml")):
                script_path = sidecar.with_suffix("")
                if not script_path.exists():
                    continue

                with open(sidecar) as f:
                    meta = yaml.safe_load(f) or {}

                name = meta.get("name") or script_path.name
                self._scripts[name] = ScriptMetadata(
                    name=name,
                    path=script_path,
                    description=meta.get("description") or "",
                    tags=list(meta.get("tags") or []),
                )

    def list(self, tag: Optional[str] = None) -> List[ScriptMetadata]:
        scripts = list(self._scripts.values())
        if tag:
            scripts = [s for s in scripts if tag in s.tags]
        return sorted(scripts, key=lambda s: s.name)

    def run(self, name: str, args: Optional[List[str]] = None) -> ScriptResult:
        """Run the named script and capture its output.

        Output is captured (not inherited from the real terminal) because
        the caller -- the TUI shell -- is actively rendering its own
        screen; a script writing directly to the real terminal's file
        descriptors while that's happening would corrupt the display.
        """
        try:
            meta = self._scripts[name]
        except KeyError as exc:
            raise ScriptNotFoundError(f"Script '{name}' is not registered") from exc

        command = [str(meta.path)] + list(args or [])
        result = subprocess.run(command, capture_output=True, text=True)
        return ScriptResult(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
