import os
import git
import json
import logging
import subprocess
import urllib.parse
from importlib import metadata

from onedep_manager.schemas import PackageDistribution
from onedep_manager.config import Config


lconfig = Config()
logger = logging.getLogger(__name__)
log_file = os.path.join(lconfig.ODM_CONFIG_DIR, "packages.log")
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


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


def install_package(source, version="latest", edit=False):
    """
    Install a package from either a package name or a path to a repository.

    Args:
        source (str): The name of the package or the path to the repository.
        version (str, optional): The version of the package to install. Defaults to "latest".
        edit (bool, optional): Whether to install the package in editable mode. Defaults to False.

    Returns:
        bool: True if the package was installed successfully, False otherwise.
    """

    if version != "latest":
        source = f"{source}=={version}"

    try:
        if edit:
            result = subprocess.run(["pip", "install", "-U", "-e", source], text=True, capture_output=True)
        else:
            result = subprocess.run(["pip", "install", "-U", source], text=True, capture_output=True)

        logger.debug(result.stdout.strip())
        logger.debug(result.stderr.strip())
    except Exception as e:
        logger.error(e)
        return False

    return True


def setup_pip_env(cs_user, cs_pass, cs_url):
    """
    Setup the pip environment with our own distribution urls.

    Returns:
        bool: True if the environment was setup successfully, False otherwise.
    """
    urlreq = urllib.parse.urlparse(cs_url)
    urlpath = "{}://{}:{}@{}{}/dist/simple/".format(urlreq.scheme, cs_user, cs_pass, urlreq.netloc, urlreq.path)

    commands = [
        ["pip", "config", "--site", "set", "global.trusted-host", urlreq.netloc],
        ["pip", "config", "--site", "set", "global.extra-index-url", "{} https://pypi.anaconda.org/OpenEye/simple".format(urlpath)],
        ["pip", "config", "--site", "set", "global.no-cache-dir", "false"],
    ]

    try:
        for command in commands:
            result = subprocess.run(command, text=True, capture_output=True)

            logger.debug(result.stdout.strip())
            logger.debug(result.stderr.strip())
    except Exception as e:
        logger.error(e)
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

        if package_name not in ONEDEP_PACKAGES:
            continue

        if name not in package_name:
            continue

        package_version = distribution.metadata["Version"]
        package_path = _get_distribution_path(distribution)
        package_branch = _get_branch(package_path) if branch else None
        package_editable = _is_editable(distribution)

        yield PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch, editable=package_editable)


def _get_branch(path):
    if path is None:
        return None

    try:
        repo = git.Repo(path)
        is_dirty = "*" if repo.is_dirty() else ""
        return f"{repo.active_branch.name}{is_dirty}"
    except TypeError:
        return repo.head.name
    except:
        return None


def switch_reference(package: PackageDistribution, reference="master"):
    try:
        repo = git.Repo(package.path)
        repo.git.checkout(reference)
    except:
        return False

    return True


def pull(package: PackageDistribution):
    try:
        repo = git.Repo(package.path)
        repo.git.pull("origin", package.branch)
    except:
        return False

    return True


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
