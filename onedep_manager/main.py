import click
from onedepmanager.cli.services import services_group
from onedepmanager.cli.tools import tools_group
from onedepmanager.cli.packages import packages_group
from onedepmanager.cli.instance import instance_group
from onedepmanager.cli.config import config_group


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

