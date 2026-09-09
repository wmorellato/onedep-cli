import click
from rich.console import Console

from onedep_manager.cli.common import get_config
from onedep_manager.instance import (
    InfoDataRetriever,
    InfoFormatter,
    InstanceInfoService,
)


def _not_implemented(command_name):
    click.echo(f"'instance {command_name}' is not implemented yet.", err=True)
    raise SystemExit(1)


@click.group(name="instance", help="Manage the current OneDep instance")
def instance_group():
    """`instance` command group"""


@instance_group.command(name="install", help="(not yet implemented) Install a new OneDep instance")
def install():
    """`install` command handler"""
    _not_implemented("install")


@instance_group.command(name="update", help="(not yet implemented) Update to the newest version")
def update():
    """`update` command handler"""
    _not_implemented("update")


@instance_group.command(name="status", help="(not yet implemented) Get a full report of the current instance")
def status():
    """`status` command handler"""
    _not_implemented("status")


@instance_group.command(name="info", help="Display basic system information")
@click.pass_context
def info(ctx):
    """`info` command handler - displays site configuration and paths"""
    console = Console()
    config = get_config(ctx)

    # Create components following dependency injection principle
    data_retriever = InfoDataRetriever(config)
    formatter = InfoFormatter(console, key_width=20)
    service = InstanceInfoService(data_retriever, formatter)

    # Display all information
    service.display_all()


