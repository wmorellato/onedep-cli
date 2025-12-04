import click
from rich.console import Console

from onedep_manager.config import Config
from onedep_manager.instance.info import (
    InfoDataRetriever,
    InfoFormatter,
    InstanceInfoService,
)


@click.group(name="instance", help="Manage the current OneDep instance")
def instance_group():
    """`instance` command group"""


@instance_group.command(name="install", help="Install a new OneDep instance")
def install():
    """`install` command handler"""


@instance_group.command(name="update", help="Update to the newest version")
def update():
    """`update` command handler"""


@instance_group.command(name="status", help="Get a full report of the current instance")
def status():
    """`status` command handler"""


@instance_group.command(name="info", help="Display basic system information")
def info():
    """`info` command handler - displays site configuration and paths"""
    console = Console()
    config = Config()

    # Create components following dependency injection principle
    data_retriever = InfoDataRetriever(config)
    formatter = InfoFormatter(console, key_width=20)
    service = InstanceInfoService(data_retriever, formatter)

    # Display all information
    service.display_all()


