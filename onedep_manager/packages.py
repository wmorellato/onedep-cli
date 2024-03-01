import os
import git
import json
import logging
import subprocess
import urllib.parse
from importlib import metadata

from onedep_manager.schemas import PackageDistribution
from onedep_manager.config import Config

logger = logging.getLogger(__name__)


ONEDEP_PACKAGES = [
    "wwpdb.utils.config",
    "wwpdb.io",
    "wwpdb.utils.db",
    "wwpdb.utils.detach",
    "wwpdb.utils.dp",
    "wwpdb.utils.emdb",
    "wwpdb.utils.markdown_wrapper",
    "wwpdb.utils.message_queue",
    "wwpdb.utils.align",
    "wwpdb.utils.nmr",
    "wwpdb.utils.cc_dict_util",
    "wwpdb.utils.oe_util",
    "wwpdb.utils.seqdb_v2",
    "wwpdb.utils.session",
    "wwpdb.utils.wf",
    "wwpdb.utils.ws_utils",
    "wwpdb.apps.wf_engine",
    "wwpdb.apps.deposit",
    "wwpdb.apps.validation",
    "wwpdb.apps.ann_tasks_v2",
    "wwpdb.apps.ccmodule",
    "wwpdb.apps.chemeditor",
    "wwpdb.apps.chem_ref_data",
    "wwpdb.apps.content_ws_server",
    "wwpdb.apps.editormodule",
    "wwpdb.apps.entity_transform",
    "wwpdb.apps.msgmodule",
    "wwpdb.apps.releasemodule",
    "wwpdb.apps.seqmodule",
    "wwpdb.apps.val_ws_server",
    "wwpdb.apps.workmanager",
    "wwpdb.apps.site_admin",
    "wwpdb.apps.val_rel",
    "wwpdb.utils.letters",
]


def install_package(source, edit=False):
    """
    Install a package from either a package name or a path to a repository.

    Args:
        source (str): The name of the package or the path to the repository.
        edit (bool, optional): Whether to install the package in editable mode. Defaults to False.

    Returns:
        bool: True if the package was installed successfully, False otherwise.
    """
    fp = open("pip.log", "w")

    try:
        if edit:
            subprocess.check_call(["pip", "install", "-U", "-e", source], stdout=fp, stderr=fp)
        else:
            subprocess.check_call(["pip", "install", "-U", source], stdout=fp, stderr=fp)
    except Exception as e:
        logger.error(e)
        return False
    finally:
        fp.close()

    return True


def setup_pip_env(cs_user, cs_pass, cs_url):
    """
    Setup the pip environment with our own distribution urls.

    Returns:
        bool: True if the environment was setup successfully, False otherwise.
    """
    fp = open("pip.log", "w")

    urlreq = urllib.parse.urlparse(cs_url)
    urlpath = "{}://{}:{}@{}{}/dist/simple/".format(urlreq.scheme, cs_user, cs_pass, urlreq.netloc, urlreq.path)

    commands = [
        ["pip", "config", "--site", "set", "global.trusted-host", urlreq.netloc],
        ["pip", "config", "--site", "set", "global.extra-index-url", "{} https://pypi.anaconda.org/OpenEye/simple".format(urlpath)],
        ["pip", "config", "--site", "set", "global.no-cache-dir", "false"],
    ]

    try:
        for command in commands:
            subprocess.check_call(command, stdout=fp, stderr=fp)
    except Exception as e:
        logger.error(e)
        return False
    finally:
        fp.close()

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
        return False

    return True


def pull(package: PackageDistribution):
    if package.branch is None:
        return False

    try:
        repo = git.Repo(package.path)
        repo.git.pull("origin", package.branch)
    except:
        return False

    return install_package(package.path, edit=package.editable)


def clone(package_name: str, reference="develop"):
    config = Config()
    source_dir = os.path.join(config.from_site("SITE_DEPLOY_PATH"), "source")

    if not os.path.exists(source_dir):
        os.makedirs(source_dir)

    package_url = f"https://github.com/{config.GITHUB_PACKAGE_HOST}/{package_name}.git"

    try:
        repo = git.Repo.clone_from(package_url, source_dir)
        repo.git.checkout(reference)
    except:
        return None

    return os.path.join(source_dir, package_name)
