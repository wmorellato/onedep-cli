import sys
import click

from onedep_manager.cli.common import ConsolePrinter, RawPrinter

from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.utils.config.ConfigInfoFileExec import ConfigInfoFileExec
from wwpdb.utils.config.ConfigInfoShellExec import ConfigInfoShellExec


@click.group(name="config", help="Query the site configuration")
def config_group():
    """`config` command group"""


@config_group.command(name="get", help="Read a value from the configuration")
@click.argument("variable", nargs=-1)
def get(variable):
    """`get` command handler"""
    ci = ConfigInfo()
    rows = []

    for v in variable:
        vcap = v.upper()
        value = ci.get(vcap)
        rows.append([vcap, str(value)])

    ConsolePrinter().table(header=["Variable", "Value"], data=rows)


@config_group.command(name="rebuild", help="Rebuild the configuration")
@click.argument("site_id")
@click.argument("location")
def rebuild(site_id, location):
    """`rebuild` command handler"""
    ci = ConfigInfoFileExec()
    ci.writeConfigCache(siteLoc=location, siteId=site_id)


@config_group.command(name="load", help="Load variables into shell environment")
@click.argument("site_id")
@click.argument("location")
def load(site_id, location):
    """`load` command handler"""
    ci = ConfigInfoShellExec(siteLoc=location, siteId=site_id, cacheFlag=False, log=sys.stderr)
    ci.shellConfig()
