import os
import click
from rich import console
from rich.theme import Theme

from onedep_manager.packages import get_package, get_wwpdb_packages, install_package, switch_reference, pull, clone, ONEDEP_PACKAGES
from onedep_manager.cli.common import ConsolePrinter



table_theme = {
    "branch_main": "dark_sea_green4",
    "branch_develop": "dark_khaki",
    "branch_other": "indian_red",
    "variable": "cyan",
    "pversion": "indian_red",
    "cversion": "dark_sea_green4",
    "sversion": "dark_khaki",
}


def _format_branch(branch, dirty=False):
    if branch is None:
        text = ""
    elif branch in ("master", "main"):
        text = f"[branch_main]{branch}[/branch_main]"
    elif branch == "develop":
        text = f"[branch_develop]{branch}[/branch_develop]"
    else:
        text = f"[branch_other]{branch}[/branch_other]"

    if dirty and branch is not None:
        text += "*"

    return text


def _format_path(path):
    if path is None:
        return ""

    onedep_root = os.environ.get("ONEDEP_PATH")

    if onedep_root and path.startswith(onedep_root):
        return path.replace(onedep_root, "[variable]${ONEDEP_PATH}[/variable]")

    return path


def _get_packages_by_name(package):
    """Helper to get packages based on 'all' or specific name.

    For `update`/`checkout`/`get`, 'all' means "every installed package whose
    name contains 'wwpdb'" — deliberately broader than ONEDEP_PACKAGES, so
    these commands also surface/manage packages installed outside that list.
    This is intentionally different from `install`'s 'all' (every name in
    ONEDEP_PACKAGES, installed or not) — see that command's docstring.
    """
    if package == "all":
        return get_wwpdb_packages(branch=True)
    return get_wwpdb_packages(name=package, branch=True)


@click.group(name="packages", help="Manage OneDep Python packages")
def packages_group():
    """`packages` command group"""


@packages_group.command(name="update", help="Updates a package to the latest remote version. If PACKAGE is set to 'all', will perform operations on all packages.")
@click.argument("package")
def update(package):
    """`update` command handler"""
    packages = _get_packages_by_name(package)
    rows = []

    c = console.Console(theme=Theme(table_theme))
    printer = ConsolePrinter(console=c)
    with c.status("Checking out packages", spinner_style="green") as s:
        for p in packages:
            s.update(f"Updating '{p.name}'...")

            if p.editable:
                pull_success = pull(package=p)
                if not pull_success:
                    printer.error(f"Failed to pull '{p.name}'. Check logs for more information.")
                    rows.append([p.name, f"[blink]{p.version}[/blink]", _format_path(p.path), _format_branch(p.branch, p.dirty)])
                    continue
                success = install_package(p.path, edit=True)
            else:
                success = install_package(p.name)

            path_text = _format_path(p.path)

            if not success:
                printer.error(f"Failed to update '{p.name}'. Check logs for more information.")
                rows.append([p.name, f"[blink]{p.version}[/blink]", path_text, _format_branch(p.branch, p.dirty)])
                continue

            upd_package = get_package(name=p.name)

            if upd_package is None:
                printer.error(f"Package '{p.name}' not found after update.")
                version_text = f"[pversion]{p.version}[/pversion] -> [cversion]?[/cversion]"
                rows.append([p.name, version_text, path_text, _format_branch(p.branch, p.dirty)])
                continue

            version_text = f"[pversion]{p.version}[/pversion] -> [cversion]{upd_package.version}[/cversion]" if p.version != upd_package.version else f"[sversion]{p.version}[/sversion]"
            rows.append([p.name, version_text, path_text, _format_branch(upd_package.branch, upd_package.dirty)])

    printer.table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="checkout", help="Checks out a package to a specific version. PACKAGE='all' operates on every installed package. REFERENCE can be a tag, branch or commit hash.")
@click.argument("package")
@click.argument("reference")
def checkout(package, reference):
    """`checkout` command handler"""
    packages = _get_packages_by_name(package)
    rows = []

    c = console.Console(theme=Theme(table_theme))
    printer = ConsolePrinter(console=c)
    with c.status("Checking out packages", spinner_style="green") as s:
        for p in packages:
            if not p.editable:
                printer.error(f"Package '{p.name}' is not in editable mode. Skipping...")
                continue

            s.update(f"Checking out '{p.name}' to '{reference}'...")
            success = switch_reference(package=p, reference=reference)

            upd_package = get_package(name=p.name)

            if upd_package is None:
                printer.error(f"Package '{p.name}' not found after checkout.")
                continue

            branch_text = _format_branch(upd_package.branch, upd_package.dirty)

            if not success:
                printer.error(f"Failed to checkout '{p.name}'")
                branch_text = f"[blink]{branch_text}[/blink]"

            path_text = _format_path(upd_package.path)
            rows.append([upd_package.name, upd_package.version, path_text, branch_text])

    printer.table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="get", help="Checks the status of a package. If PACKAGE is set to 'all', will perform operations on all packages.")
@click.argument("package")
def get(package):
    """`get` command handler"""
    packages = _get_packages_by_name(package)
    rows = []

    for pkg in packages:
        branch_text = _format_branch(pkg.branch, pkg.dirty)
        path_text = _format_path(pkg.path)
        rows.append([pkg.name, pkg.version, path_text, branch_text])

    c = console.Console(theme=Theme(table_theme))
    ConsolePrinter(console=c).table(header=["Package", "Version", "Location", "Branch"], data=rows)


@packages_group.command(name="install", help="Installs a package. PACKAGE='all' installs every ONEDEP_PACKAGES entry (unlike update/checkout/get's 'all' — see the docstring).")
@click.argument("package")
@click.option("-d", "--dev", "dev", is_flag=True, default=False, help="If set, will install the package in development mode.")
def install(package, dev):
    """`install` command handler.

    'all' here means "every name in ONEDEP_PACKAGES" (installed or not) so a
    fresh instance can be bootstrapped from nothing. This is intentionally
    different from `update`/`checkout`/`get`'s 'all', which only ever
    operates on packages that are already installed — see
    `_get_packages_by_name`.
    """
    c = console.Console(theme=Theme(table_theme))
    printer = ConsolePrinter(console=c)

    if package == "all":
        packages = ONEDEP_PACKAGES
    else:
        if package not in ONEDEP_PACKAGES:
            printer.error(f"Package '{package}' is not a OneDep package.")
            return

        packages = [package]

    rows = []

    with c.status("Installing packages", spinner_style="green") as s:
        for pkg_name in packages:
            s.update(f"Installing '{pkg_name}'...")

            if dev:
                repo_name = f"py-{pkg_name.replace('.', '_')}"
                pkg_path = clone(package_name=repo_name, reference="develop")
                if pkg_path is None:
                    printer.error(f"Failed to clone '{pkg_name}'")
                    continue

                success = install_package(pkg_path, edit=True)
            else:
                success = install_package(pkg_name)

            if not success:
                printer.error(f"Failed to install '{pkg_name}'")
                continue

            installed_pkg = get_package(name=pkg_name, branch=True)

            if installed_pkg is not None:
                rows.append([installed_pkg.name, installed_pkg.version, _format_path(installed_pkg.path), _format_branch(installed_pkg.branch, installed_pkg.dirty)])

    printer.table(header=["Package", "Version", "Location", "Branch"], data=rows)
