import os
import sys
import click
import subprocess
from rich.console import Console
from rich.theme import Theme

from onedep_manager.cli.common import ConsolePrinter

from wwpdb.utils.config.ConfigInfo import ConfigInfo, getSiteId
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

    c = Console()
    ConsolePrinter(console=c).table(header=["Variable", "Value"], data=rows)


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


@config_group.command(name="edit", help="Edit the configuration file")
@click.option("-i", "--site", "site", help="wwPDB site ID (e.g. WWPDB_DEPLOY_TEST_RU). Defaults to the current site.")
@click.option("-r", "--rebuild", "rebuild", help="If set, will rebuild the configuration after editing.")
def edit(site, rebuild):
    """`edit` command handler"""
    c = Console()
    printer = ConsolePrinter(console=c)

    if not site:
        site = getSiteId()
    
    ci = ConfigInfo(siteId=site)
    site_config_path = ci.get("WWPDB_SITE_CONFIG_DIR")

    if not site_config_path or not os.path.exists(site_config_path):
        printer.error(f"Site configuration for {site} does not exist")
        return

    site_config_file = os.path.join(site_config_path, "site.cfg")
    printer.info(f"Editing {site_config_file}")
    # put the file viewer in the config
    subprocess.run(["vi", site_config_file])
