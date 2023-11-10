from click.testing import CliRunner
from onedep_manager.cli.packages import status
from onedep_manager.schemas import PackageDistribution


def test_status(monkeypatch):
    monkeypatch.setattr(
        "onedep_manager.cli.packages.get_wwpdb_packages",
        lambda prefix=None, branch=None: [
            PackageDistribution(name="wwpdb.utils.config", version="0.1.0", path="/foo/bar/wwpdb.utils.config", branch="master"),
            PackageDistribution(name="wwpdb.utils.foobar", version="0.2.0", path="/foo/bar/wwpdb.utils.foobar")
        ]
    )

    runner = CliRunner()
    result = runner.invoke(status, ["all"])
    print(result.output)

    assert result.exit_code == 0
    assert "wwpdb.utils.config" in result.output
    assert "0.1.0" in result.output
    assert "/foo/bar/wwpdb.utils.config" in result.output
    assert "master" in result.output

    assert "wwpdb.utils.foobar" in result.output
    assert "0.2.0" in result.output
    assert "/foo/bar/wwpdb.utils.foobar" in result.output
