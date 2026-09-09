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
_logging_configured = False


def _configure_logging():
    """Attach handlers to the module logger on first use.

    Deferred so importing this module doesn't do filesystem I/O (Config()
    construction, log file creation) as a side effect.
    """
    global _logging_configured

    if _logging_configured:
        return

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # File logging needs a working site Config(); if that fails (e.g. no
    # site configured), fall back to console-only rather than letting a
    # logging-setup failure break the git/pip operation being logged.
    try:
        config = Config()
        log_file = os.path.join(config.ODM_CONFIG_DIR, "packages.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception:
        logger.debug("Could not set up file logging for packages.log; using console logging only.", exc_info=True)

    _logging_configured = True


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

    _configure_logging()

    if version != "latest":
        source = f"{source}=={version}"

    try:
        if edit:
            result = subprocess.run(["pip", "install", "-U", "-e", source], text=True, capture_output=True)
        else:
            result = subprocess.run(["pip", "install", "-U", source], text=True, capture_output=True)
    except OSError as e:
        logger.error(e)
        return False

    logger.debug(result.stdout.strip())
    logger.debug(result.stderr.strip())

    if result.returncode != 0:
        logger.error("pip install failed for '%s': %s", source, result.stderr.strip())
        return False

    return True


def setup_pip_env(cs_user, cs_pass, cs_url):
    """
    Setup the pip environment with our own distribution urls.

    Returns:
        bool: True if the environment was setup successfully, False otherwise.
    """
    _configure_logging()

    urlreq = urllib.parse.urlparse(cs_url)
    urlpath = "{}://{}:{}@{}{}/dist/simple/".format(urlreq.scheme, cs_user, cs_pass, urlreq.netloc, urlreq.path)

    commands = [
        ["pip", "config", "--site", "set", "global.trusted-host", urlreq.netloc],
        ["pip", "config", "--site", "set", "global.extra-index-url", "{} https://pypi.anaconda.org/OpenEye/simple".format(urlpath)],
        ["pip", "config", "--site", "set", "global.no-cache-dir", "false"],
    ]

    for command in commands:
        try:
            result = subprocess.run(command, text=True, capture_output=True)
        except OSError as e:
            logger.error(e)
            return False

        logger.debug(result.stdout.strip())
        logger.debug(result.stderr.strip())

        if result.returncode != 0:
            logger.error("Command failed: %s -> %s", " ".join(command), result.stderr.strip())
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
    package_dirty = _is_dirty(package_path) if branch else False
    package_editable = _is_editable(distribution)

    return PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch, dirty=package_dirty, editable=package_editable)


def get_wwpdb_packages(name="wwpdb", branch=True):
    # need a separate function for resources_rx and web apps
    distributions = metadata.distributions()

    for distribution in distributions:
        package_name = distribution.metadata["Name"] # had some issues accessing distribution.name directly

        if name not in package_name:
            continue

        package_version = distribution.metadata["Version"]
        package_path = _get_distribution_path(distribution)
        package_branch = _get_branch(package_path) if branch else None
        package_dirty = _is_dirty(package_path) if branch else False
        package_editable = _is_editable(distribution)

        yield PackageDistribution(name=package_name, version=package_version, path=package_path, branch=package_branch, dirty=package_dirty, editable=package_editable)


def _get_branch(path):
    """Return the plain branch/ref name for the repo at `path`, or None.

    Display-only decoration (e.g. a dirty marker) does not belong here:
    this value is also used verbatim as a git ref by callers like pull().
    See _is_dirty() for the dirty-state flag.
    """
    if path is None:
        return None

    try:
        repo = git.Repo(path)
        return repo.active_branch.name
    except TypeError:
        return repo.head.name
    except git.GitError as e:
        logger.debug("Could not read branch for '%s': %s", path, e)
        return None


def _is_dirty(path):
    if path is None:
        return False

    try:
        repo = git.Repo(path)
        return repo.is_dirty()
    except git.GitError as e:
        logger.debug("Could not read dirty state for '%s': %s", path, e)
        return False


def switch_reference(package: PackageDistribution, reference="master"):
    _configure_logging()

    try:
        repo = git.Repo(package.path)
        repo.git.checkout(reference)
    except git.GitError as e:
        logger.error("Failed to checkout '%s' to '%s': %s", package.name, reference, e)
        return False

    return True


def pull(package: PackageDistribution):
    _configure_logging()

    try:
        repo = git.Repo(package.path)
        repo.git.pull("origin", package.branch)
    except git.GitError as e:
        logger.error("Failed to pull '%s': %s", package.name, e)
        return False

    return True


def clone(package_name: str, reference="develop"):
    _configure_logging()

    config = Config()
    source_dir = os.path.join(config.from_site("SITE_DEPLOY_PATH"), "source")
    package_dir = os.path.join(source_dir, package_name)

    if not os.path.exists(source_dir):
        os.makedirs(source_dir)

    package_url = f"https://github.com/{config.GITHUB_PACKAGE_HOST}/{package_name}.git"

    try:
        repo = git.Repo.clone_from(package_url, package_dir)
        repo.git.checkout(reference)
    except git.GitError as e:
        logger.error("Failed to clone '%s': %s", package_name, e)
        return None

    return package_dir
