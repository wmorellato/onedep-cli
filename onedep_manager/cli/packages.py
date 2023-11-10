import click

from onedep_manager.packages import get_wwpdb_packages
from onedep_manager.cli.common import ConsolePrinter


branch_theme = {
    "main": "green",
    "develop": "yellow",
    "other": "red",
}


@click.group(name="packages", help="Manage OneDep Python packages")
def packages_group():
    """`packages` command group"""


@packages_group.command(name="upgrade", help="Upgrades a package to the latest version. If PACKAGE_NAME is set to 'all', will perform operations on all packages.")
@click.argument("package")
def upgrade(package):
    """`upgrade` command handler"""


@packages_group.command(name="checkout", help="Checks out a package to a specific version. If PACKAGE_NAME is set to 'all', will perform operations on all packages.")
@click.argument("version")
@click.argument("package")
def checkout(version, package):
    """`checkout` command handler"""


@packages_group.command(name="status", help="Check the status of a package. If PACKAGE_NAME is set to 'all', will perform operations on all packages.")
@click.argument("package")
def status(package):
    """`status` command handler"""
    if package == "all":
        packages = get_wwpdb_packages(branch=True)
    else:
        packages = get_wwpdb_packages(prefix=package, branch=True)

    rows = []
    for s in packages:
        if s.branch in ("master", "main"):
            branch_text = f"[main]{s.branch}[/main]"
        elif s.branch == "develop":
            branch_text = f"[develop]{s.branch}[/develop]"
        elif s.branch is None:
            branch_text = f""
        else:
            branch_text = f"[other]{s.branch}[/other]"
        rows.append([s.name, s.version, s.path, branch_text])

    ConsolePrinter(theme=branch_theme).table(header=["Package", "Version", "Location", "Branch"], data=rows)
