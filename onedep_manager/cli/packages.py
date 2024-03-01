import click
from rich import console
from rich.theme import Theme

from onedep_manager.packages import get_package, get_wwpdb_packages, install_package, switch_reference, pull, clone, ONEDEP_PACKAGES
from onedep_manager.cli.common import ConsolePrinter

from wwpdb.utils.config.ConfigInfo import ConfigInfo


table_theme = {
    "branch_main": "dark_sea_green4",
    "branch_develop": "dark_khaki",
    "branch_other": "indian_red",
    "variable": "cyan",
    "pversion": "indian_red",
    "cversion": "dark_sea_green4",
    "sversion": "dark_khaki",
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
        return path.replace(onedep_root, "[variable]${ONEDEP_PATH}[/variable]")

    return path


@click.group(name="packages", help="Manage OneDep Python packages")
def packages_group():
    """`packages` command group"""


@packages_group.command(name="update", help="Updates a package to the latest remote version. If PACKAGE is set to 'all', will perform operations on all packages.")
@click.argument("package")
def update(package):
    """`update` command handler"""
    if package == "all":
        packages = get_wwpdb_packages(branch=True)
    else:
        packages = get_wwpdb_packages(name=package, branch=True)

    rows = []

    c = console.Console(theme=Theme(table_theme))
    with c.status("Checking out packages", spinner_style="green") as s:
        for p in packages:
            s.update(f"Updating '{p.name}'...")
            success = pull(package=p)

            path_text = _format_path(p.path)

            if not success:
                c.log(f"Failed to update '{p.name}'")
                rows.append([p.name, f"[blink]{p.version}[/blink]", path_text, p.branch])
                continue

            upd_package = get_package(name=p.name)

            if upd_package is None:
                version_text = f"[pversion]{p.version}[/pversion] -> [cversion]?[/cversion]"
                rows.append([p.name, version_text, path_text, p.branch])
                continue

            if p.version != upd_package.version:
                version_text = f"[pversion]{p.version}[/pversion] -> [cversion]{upd_package.version}[/cversion]"
            else:
                version_text = f"[sversion]{p.version}[/sversion]"

            rows.append([p.name, version_text, path_text, p.branch])

    ConsolePrinter(console=c).table(header=["Package", "Version", "Location", "Branch"], data=rows)


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

    c = console.Console(theme=Theme(table_theme))
    with c.status("Checking out packages", spinner_style="green") as s:
        for p in packages:
            s.update(f"Checking out '{p.name}' to '{reference}'...")
            success = switch_reference(package=p, reference=reference)

            upd_package = get_package(name=p.name)
            branch_text = _format_branch(upd_package.branch)

            if not success:
                c.log(f"Failed to checkout '{p.name}'")
                branch_text = f"[blink]{branch_text}[/blink]"

            path_text = _format_path(p.path)
            rows.append([p.name, p.version, path_text, branch_text])

    ConsolePrinter(console=c).table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="get", help="Checks the status of a package. If PACKAGE is set to 'all', will perform operations on all packages.")
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

    c = console.Console(theme=Theme(table_theme))
    ConsolePrinter(console=c).table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="install", help="Installs a package")
@click.argument("package")
@click.option("-d", "--dev", "dev", is_flag=True, default=False, help="If set, will install the package in development mode.")
def install(package, dev):
    """`install` command handler"""
    if package == "all":
        packages = ONEDEP_PACKAGES
    else:
        packages = [package]

    rows = []

    c = console.Console(theme=Theme(table_theme))
    with c.status("Installing packages", spinner_style="green") as s:
        for p in packages:
            s.update(f"Installing '{p}'...")

            if dev:
                ppath = clone(package_name=p, reference="develop")
                if ppath is None:
                    c.log(f"Failed to install '{p}'")
                    continue

                success = install_package(ppath, edit=True)
            else:
                success = install_package(p)

            if not success:
                c.log(f"Failed to install '{p}'")

            stripped_name = package.replace("py-wwpdb-utils", "").replace("py-wwpdb-apps", "")
            package = get_package(name=stripped_name, branch=True)
            rows.append([package.name, package.version, package.path, package.branch])

    ConsolePrinter(console=c).table(header=["Package", "Version", "Location", "Branch"], data=rows)
