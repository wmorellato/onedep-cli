import pytest

from onedep_manager.config import Config


def test_get_services():
    config = Config("tests/fixtures/config.yaml")

    assert len(config.get_services()) == 2
    assert config.get_services()[0].name == "apache"
    assert config.get_services()[1].name == "foo"


def test_single_service():
    config = Config("tests/fixtures/config.yaml")

    assert config.get_service("apache").name == "apache"
    assert config.get_service("apache").handler == "onedep_manager.tests.test_services.HandlerTest"

    with pytest.raises(Exception):
        config.get_service("bar")
