import os
import git
import json
import logging
import urllib.parse
from importlib import metadata

from onedep_manager.schemas import PackageDistribution


def _get_distribution_path(distribution: metadata.Distribution):
    path = os.path.dirname(distribution._path) # if pip can, why can't I?

    if path.endswith("site-packages"):
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
    

def get_wwpdb_packages(prefix="wwpdb", branch=True):
    distributions = metadata.distributions()

    for distribution in distributions:
        package_name = distribution.metadata["Name"] # had some issues accessing distribution.name directly

        # maybe get the list of wwpdb packages from a config file?
        if not package_name.startswith(prefix):
            continue

        package_version = distribution.metadata["Version"]
        package_path = _get_distribution_path(distribution)
        package_branch = _get_branch(package_path) if branch else None

        yield PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch)


def checkout_wwpdb_packages(prefix="wwpdb", reference="master"):
    for package in get_wwpdb_packages(prefix=prefix):
        if package.branch is None:
            continue

        try:
            repo = git.Repo(package.path)
            repo.git.checkout(reference)
        except:
            logging.warning(f"Could not checkout '{package.name}' to '{reference}'")
            yield package, False
            continue

        # check the branch again
        package.branch = _get_branch(package.path)
        yield package, True
