from pathlib import Path
from typing import Callable, Dict, Optional


class UnknownRepositoryError(Exception):
    """Raised when EntryPathResolver.resolve() is asked for an unsupported repo name."""


_REPO_GETTERS: Dict[str, Callable] = {
    "tempdep": lambda pi, entry_id: pi.getTempDepPath(dataSetId=entry_id),
    "deposit": lambda pi, entry_id: pi.getDepositPath(dataSetId=entry_id),
    "deposit-ui": lambda pi, entry_id: pi.getDepositUIPath(dataSetId=entry_id),
    "archive": lambda pi, entry_id: pi.getArchivePath(dataSetId=entry_id),
    "upload": lambda pi, entry_id: pi.getDirPath(dataSetId=entry_id, fileSource="uploads"),
    "pickles": lambda pi, entry_id: pi.getDirPath(dataSetId=entry_id, fileSource="pickles"),
}


class EntryPathResolver:
    """Resolves an entry id + repository name to a filesystem path.

    Wraps wwPDB's PathInfo. The real PathInfo is only imported inside
    __init__ when no `path_info` is injected, so importing this module
    (and constructing a resolver with an injected fake) never requires
    wwpdb.io to be installed -- only calling .resolve() with the real,
    lazily-constructed PathInfo does.
    """

    def __init__(self, path_info=None, site: Optional[str] = None):
        if path_info is None:
            from wwpdb.io.locator.PathInfo import PathInfo

            path_info = PathInfo(siteId=site)
        self._path_info = path_info

    def resolve(self, entry_id: str, repo: str) -> Path:
        try:
            getter = _REPO_GETTERS[repo]
        except KeyError as exc:
            raise UnknownRepositoryError(f"Unknown repository '{repo}'. Valid repositories: {', '.join(sorted(_REPO_GETTERS))}") from exc
        return Path(getter(self._path_info, entry_id))

    @property
    def known_repos(self):
        return sorted(_REPO_GETTERS)
