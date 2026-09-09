import click

from onedep_manager.cli.common import get_config
from onedep_manager.shell.app import OneDepShell


@click.command(name="shell", help="Launch the interactive OneDep shell")
@click.option("-i", "--site", "site", help="wwPDB site ID (e.g. WWPDB_DEPLOY_TEST_RU). Defaults to the current site.")
@click.pass_context
def shell(ctx, site):
    config = get_config(ctx)
    OneDepShell(config=config, site=site).cmdloop()
