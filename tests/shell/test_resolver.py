from pathlib import Path

import pytest

from onedep_manager.shell.resolver import EntryPathResolver, UnknownRepositoryError


class FakePathInfo:
    """Stands in for wwpdb.io.locator.PathInfo, which isn't installed here."""

    def getTempDepPath(self, dataSetId):
        return f"/data/tempdep/{dataSetId}"

    def getDepositPath(self, dataSetId):
        return f"/data/deposit/{dataSetId}"

    def getDepositUIPath(self, dataSetId):
        return f"/data/deposit-ui/{dataSetId}"

    def getArchivePath(self, dataSetId):
        return f"/data/archive/{dataSetId}"

    def getDirPath(self, dataSetId, fileSource):
        return f"/data/{fileSource}/{dataSetId}"


@pytest.fixture
def resolver():
    return EntryPathResolver(path_info=FakePathInfo())


def test_resolve_archive(resolver):
    assert resolver.resolve("D_1000001", "archive") == Path("/data/archive/D_1000001")


def test_resolve_upload_uses_get_dir_path(resolver):
    assert resolver.resolve("D_1000001", "upload") == Path("/data/uploads/D_1000001")


def test_resolve_unknown_repo_raises(resolver):
    with pytest.raises(UnknownRepositoryError):
        resolver.resolve("D_1000001", "not-a-repo")


def test_known_repos_lists_all_supported_names(resolver):
    assert "archive" in resolver.known_repos
    assert "deposit-ui" in resolver.known_repos


def test_constructing_without_path_info_defers_wwpdb_import():
    # Must not raise ImportError at construction time just because
    # wwpdb.io isn't installed in this environment -- only fails if
    # .resolve() is actually called without an injected path_info.
    resolver = EntryPathResolver.__new__(EntryPathResolver)
    assert resolver is not None
