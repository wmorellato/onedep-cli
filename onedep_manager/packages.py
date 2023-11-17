import os
import git
import json
import logging
import subprocess
import urllib.parse
from importlib import metadata

from onedep_manager.schemas import PackageDistribution


def install_package(source, edit=False):
    """
    Install a package from either a package name or a path to a repository.

    Args:
        source (str): The name of the package or the path to the repository.
        edit (bool, optional): Whether to install the package in editable mode. Defaults to False.

    Returns:
        bool: True if the package was installed successfully, False otherwise.
    """
    try:
        if edit:
            subprocess.check_call(["pip", "install", "-U", "-e", source])
        else:
            subprocess.check_call(["pip", "install", "-U", source])
    except Exception as e:
        logging.error(e)
        return False
    
    return True


def _is_editable(distribution: metadata.Distribution):
    path = os.path.dirname(distribution._path)

    if path is None:
        return False

    if path.endswith("site-packages"):
        return False
    
    return True


def _get_distribution_path(distribution: metadata.Distribution):
    path = os.path.dirname(distribution._path) # if pip can, why can't I?

    if path is not None and path.endswith("site-packages"):
        # this is not accurate, as the package could be installed somewhere else
        # try to get the source location from 'direct_url.json'
        direct_url_path = os.path.join(distribution._path, "direct_url.json")

        if not os.path.exists(direct_url_path):
            # probably installed from pypi
            return None

        with open(direct_url_path) as f:
            data = json.load(f)
            spath = urllib.parse.urlparse(data["url"]).path

        if not os.path.exists(spath):
            # the source path does not exist
            return None
        
        return spath

    return path


def _get_branch(path):
    if path is None:
        return None

    try:
        repo = git.Repo(path)
        return repo.active_branch.name
    except TypeError:
        return repo.head.name
    except:
        return None


def get_package(name, branch=True):
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return None
    
    package_name = distribution.metadata["Name"]
    package_version = distribution.metadata["Version"]
    package_path = _get_distribution_path(distribution)
    package_branch = _get_branch(package_path) if branch else None
    package_editable = _is_editable(distribution)

    return PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch, editable=package_editable)


def get_wwpdb_packages(name="wwpdb", branch=True):
    distributions = metadata.distributions()

    for distribution in distributions:
        package_name = distribution.metadata["Name"] # had some issues accessing distribution.name directly

        # maybe get the list of wwpdb packages from a config file?
        if not package_name.startswith("wwpdb"):
            continue

        if name not in package_name:
            continue

        package_version = distribution.metadata["Version"]
        package_path = _get_distribution_path(distribution)
        package_branch = _get_branch(package_path) if branch else None
        package_editable = _is_editable(distribution)

        yield PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch, editable=package_editable)


def switch_reference(package: PackageDistribution, reference="master"):
    # stil need to check if package is in edit mode
    if package.branch is None:
        return False

    try:
        repo = git.Repo(package.path)
        repo.git.checkout(reference)
    except:
        logging.warning(f"Could not checkout '{package.name}' to '{reference}'")
        return False

    return True


def pull(package: PackageDistribution):
    if package.branch is None:
        return False

    try:
        repo = git.Repo(package.path)
        repo.git.pull("origin", package.branch)
    except:
        logging.warning(f"Could not pull '{package.name}' to '{package.branch}'")
        return False

    return install_package(package.path, edit=package.editable)
