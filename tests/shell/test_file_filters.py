from pathlib import Path

from onedep_manager.shell.file_filters import filter_files, parse_wwpdb_filename


def test_parse_valid_filename():
    attrs = parse_wwpdb_filename(Path("D_800000_model_P1.cif.V2"))

    assert attrs.dataset == "D_800000"
    assert attrs.content_type == "model"
    assert attrs.part == 1
    assert attrs.format == "cif"
    assert attrs.version == 2


def test_parse_filename_with_hyphenated_content_type():
    attrs = parse_wwpdb_filename(Path("D_800000_model-upload_P1.cif.V1"))

    assert attrs.content_type == "model-upload"


def test_parse_non_wwpdb_filename_returns_none():
    assert parse_wwpdb_filename(Path("README.md")) is None


def _paths(*names):
    return [Path(n) for n in names]


def test_filter_by_type():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_sf_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
    )

    matched = filter_files(files, types=["model"])

    assert [a.path.name for a in matched] == ["D_800000_model_P1.cif.V1"]


def test_filter_by_multiple_types():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_sf_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
    )

    matched = filter_files(files, types=["model", "model-upload"])

    names = {a.path.name for a in matched}
    assert names == {"D_800000_model_P1.cif.V1", "D_800000_model-upload_P1.cif.V1"}


def test_filter_by_milestone_matches_hyphen_suffix():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model-upload_P1.cif.V1",
        "D_800000_sf-upload_P1.cif.V1",
    )

    matched = filter_files(files, milestone="upload")

    names = {a.path.name for a in matched}
    assert names == {"D_800000_model-upload_P1.cif.V1", "D_800000_sf-upload_P1.cif.V1"}


def test_filter_by_exact_version():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model_P1.cif.V2",
    )

    matched = filter_files(files, version="1")

    assert [a.version for a in matched] == [1]


def test_filter_by_latest_version_groups_by_dataset_type_part_format():
    files = _paths(
        "D_800000_model_P1.cif.V1",
        "D_800000_model_P1.cif.V2",
        "D_800000_model_P1.cif.V3",
        "D_800000_sf_P1.cif.V1",
    )

    matched = filter_files(files, version="latest")

    versions_by_type = {a.content_type: a.version for a in matched}
    assert versions_by_type == {"model": 3, "sf": 1}


def test_filter_skips_unparseable_files():
    files = _paths("D_800000_model_P1.cif.V1", "not_wwpdb.txt")

    matched = filter_files(files, types=["model"])

    assert len(matched) == 1
