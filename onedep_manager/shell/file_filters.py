import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_FILENAME_RE = re.compile(
    r"^(?P<dataset>D_\d+)_(?P<content_type>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)_P(?P<part>\d+)"
    r"\.(?P<format>[A-Za-z0-9]+)\.V(?P<version>\d+)$"
)


@dataclass(frozen=True)
class FileAttributes:
    path: Path
    dataset: str
    content_type: str
    part: int
    format: str
    version: int


def parse_wwpdb_filename(path: Path) -> Optional[FileAttributes]:
    """Parse a wwPDB-convention filename, e.g. D_800000_model_P1.cif.V2.

    Returns None for filenames that don't match the convention, rather
    than raising, so callers can filter a mixed directory listing.
    """
    match = _FILENAME_RE.match(path.name)
    if not match:
        return None

    return FileAttributes(
        path=path,
        dataset=match.group("dataset"),
        content_type=match.group("content_type"),
        part=int(match.group("part")),
        format=match.group("format"),
        version=int(match.group("version")),
    )


def filter_files(
    files: Sequence[Path],
    types: Optional[Sequence[str]] = None,
    milestone: Optional[str] = None,
    version: Optional[str] = None,
) -> List[FileAttributes]:
    parsed = [a for a in (parse_wwpdb_filename(f) for f in files) if a is not None]

    if types:
        type_set = set(types)
        parsed = [a for a in parsed if a.content_type in type_set]

    if milestone:
        suffix = f"-{milestone}"
        parsed = [a for a in parsed if a.content_type.endswith(suffix)]

    if version == "latest":
        parsed = _latest_only(parsed)
    elif version is not None:
        parsed = [a for a in parsed if a.version == int(version)]

    return parsed


def _latest_only(attrs: List[FileAttributes]) -> List[FileAttributes]:
    latest: Dict[Tuple[str, str, int, str], FileAttributes] = {}

    for a in attrs:
        key = (a.dataset, a.content_type, a.part, a.format)
        if key not in latest or a.version > latest[key].version:
            latest[key] = a

    return list(latest.values())
