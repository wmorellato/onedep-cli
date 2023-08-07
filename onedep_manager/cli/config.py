import sys
import click

from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.utils.config.ConfigInfoFileExec import ConfigInfoFileExec


@click.group(name="config", help="Query the site configuration")
def config_group():
    """`config` command group"""


@config_group.command(name="get", help="Read a value from the configuration")
@click.argument("variable", nargs=-1)
def get(variable):
    """`get` command handler"""
    ci = ConfigInfo()

    for v in variable:
        vcap = v.upper()
        value = ci.get(vcap)
        color = "green"

        if not value:
            color = "red"

        click.echo(f"{click.style(vcap, fg=color)}: {ci.get(vcap)}")


@config_group.command(name="rebuild", help="Rebuild the configuration")
@click.argument("site_id")
@click.argument("location")
def rebuild(site_id, location):
    """`rebuild` command handler"""
    ci = ConfigInfoFileExec()
    ci.writeConfigCache(siteLoc=location, siteId=site_id)


@config_group.command(name="load", help="Load variables into shell environment")
def load():
    """`load` command handler"""
