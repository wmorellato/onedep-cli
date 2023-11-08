import os
import json
from importlib import metadata

from onedep_manager.schemas import PackageDistribution


def _get_distribution_path(distribution: metadata.Distribution):
    path = os.path.dirname(distribution._path) # if pip can, why can't I?

    if path.endswith("site-packages"):
        # try to get the source location from 'direct_url.json'
        direct_url_path = os.path.join(distribution._path, "direct_url.json")

        if not os.path.exists(direct_url_path):
            # probably installed from pypi
            return None

        with open(direct_url_path) as f:
            data = json.load(f)
            spath = data["url"]

        if not os.path.exists(spath):
            # the source path does not exist
            return None
        
        return os.path.dirname(spath)

    return path


def get_wwpdb_packages():
    distributions = metadata.distributions()

    for distribution in distributions:
        package_name = distribution.metadata["Name"] # had some issues accessing distribution.name directly

        # maybe get the list of wwpdb packages from a config file?
        if not package_name.startswith("wwpdb"):
            continue

        package_version = distribution.metadata["Version"]
        package_path = _get_distribution_path(distribution)

        yield PackageDistribution(name=package_name, version=package_version, path=package_path)


if __name__ == "__main__":
    for package in get_wwpdb_packages():
        print(package)
