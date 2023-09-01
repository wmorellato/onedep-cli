import os
import pytest
from click.testing import CliRunner
from unittest import mock

from onedep_manager.cli.services import start


def test_start_service():
    runner = CliRunner()
    result = runner.invoke(start, ["service"])

    assert result.exit_code == 0
    assert result.output == "service started succesfully\nStatus: running\n"
