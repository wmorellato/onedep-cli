import click

from wwpdb.utils.config.ConfigInfo import ConfigInfo


@click.group(name="config", help="Query the site configuration")
def config_group():
    """`config` command group"""


@config_group.command(name="get", help="Read a value from the configuration")
@click.argument("variable", nargs=-1)
def get(variable):
    """`get` command handler"""
    ci = ConfigInfo()

    for v in variable:
        click.echo(f"{v}: {ci.get(v)}")


@config_group.command(name="rebuild", help="Rebuilds the configuration")
def rebuild():
    """`rebuild` command handler"""
