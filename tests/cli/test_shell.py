from unittest import mock

from click.testing import CliRunner

from onedep_manager.cli.common import CLIContext
from onedep_manager.cli.shell import shell


def test_shell_command_constructs_and_runs_cmdloop():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepShell") as MockShell:
        instance = MockShell.return_value
        result = runner.invoke(shell, [], obj=CLIContext(config=mock.Mock()))

    assert result.exit_code == 0
    instance.cmdloop.assert_called_once()


def test_shell_command_passes_site_option_through():
    runner = CliRunner()

    with mock.patch("onedep_manager.cli.shell.OneDepShell") as MockShell:
        runner.invoke(shell, ["--site", "WWPDB_DEPLOY_TEST_RU"], obj=CLIContext(config=mock.Mock()))

    _, kwargs = MockShell.call_args
    assert kwargs["site"] == "WWPDB_DEPLOY_TEST_RU"


def test_shell_help():
    runner = CliRunner()
    result = runner.invoke(shell, ["--help"])

    assert result.exit_code == 0
    assert "shell" in result.output.lower()
