import click

from onedep_manager.packages import get_wwpdb_packages, switch_reference
from onedep_manager.cli.common import ConsolePrinter

from wwpdb.utils.config.ConfigInfo import ConfigInfo


table_theme = {
    "branch_main": "dark_sea_green4",
    "branch_develop": "dark_khaki",
    "branch_other": "indian_red",
    "variable": "cyan",
}


def _format_branch(branch):
    if branch in ("master", "main"):
        return f"[branch_main]{branch}[/branch_main]"
    elif branch == "develop":
        return f"[branch_develop]{branch}[/branch_develop]"
    elif branch is None:
        return f""
    else:
        return f"[branch_other]{branch}[/branch_other]"


def _format_path(path):
    if path is None:
        return ""

    config = ConfigInfo()
    onedep_root = config.get("TOP_SOFTWARE_DIR")

    if path.startswith(onedep_root):
        return path.replace(onedep_root, "[variable]${TOP_SOFTWARE_DIR}[/variable]")

    return path


@click.group(name="packages", help="Manage OneDep Python packages")
def packages_group():
    """`packages` command group"""


@packages_group.command(name="upgrade", help="Upgrades a package to the latest version. If PACKAGE is set to 'all', will perform operations on all packages.")
@click.argument("package")
def upgrade(package):
    """`upgrade` command handler"""


@packages_group.command(name="checkout", help="Checks out a package to a specific version. If PACKAGE is set to 'all', will perform operations on all packages. REFERENCE can be a tag, branch or commit hash.")
@click.argument("package")
@click.argument("reference")
def checkout(package, reference):
    """`checkout` command handler"""
    if package == "all":
        packages = get_wwpdb_packages(branch=True)
    else:
        packages = get_wwpdb_packages(name=package, branch=True)

    rows = []
    for p in packages:
        success = switch_reference(reference=reference)
        branch_text = _format_branch(p.branch)

        if not success:
            branch_text = f"[blink]{branch_text}[/blink]"

        path_text = _format_path(p.path)
        rows.append([p.name, p.version, path_text, branch_text])

    ConsolePrinter(theme=table_theme).table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="get", help="Check the status of a package. If PACKAGE is set to 'all', will perform operations on all packages.")
@click.argument("package")
def get(package):
    """`get` command handler"""
    if package == "all":
        packages = get_wwpdb_packages(branch=True)
    else:
        packages = get_wwpdb_packages(name=package, branch=True)

    rows = []
    for s in packages:
        branch_text = _format_branch(s.branch)
        path_text = _format_path(s.path)
        rows.append([s.name, s.version, path_text, branch_text])

    ConsolePrinter(theme=table_theme).table(header=["Package", "Version", "Location", "Branch"], data=rows)
