import click

from onedep_manager.packages import get_wwpdb_packages
from onedep_manager.cli.common import ConsolePrinter

from wwpdb.utils.config.ConfigInfo import ConfigInfo


table_theme = {
    "branch_main": "green",
    "branch_develop": "yellow",
    "branch_other": "red",
    "variable": "cyan",
}


def _format_branch(branch):
    if branch in ("master", "main"):
        return f"[main]{branch}[/main]"
    elif branch == "develop":
        return f"[develop]{branch}[/develop]"
    elif branch is None:
        return f""
    else:
        return f"[other]{branch}[/other]"


def _format_path(path):
    config = ConfigInfo()
    onedep_root = config.get("TOP_SOFTWARE_DIR")

    if path.startswith(onedep_root):
        return path.replace(onedep_root, "[variable]${TOP_SOFTWARE_DIR}[/variable]")

    return path


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
        branch_text = _format_branch(s.branch)
        path_text = _format_path(s.path)
        rows.append([s.name, s.version, path_text, branch_text])

    ConsolePrinter(theme=table_theme).table(header=["Package", "Version", "Location", "Branch"], data=rows)
