import click
from onedep_manager.cli.services import services_group
from onedep_manager.cli.tools import tools_group
from onedep_manager.cli.packages import packages_group
from onedep_manager.cli.instance import instance_group
from onedep_manager.cli.config import config_group


@click.group()
def cli():
    """CLI entry point"""


cli.add_command(services_group)
cli.add_command(tools_group)
cli.add_command(packages_group)
cli.add_command(instance_group)
cli.add_command(config_group)


if __name__ == "__main__":
    cli()

