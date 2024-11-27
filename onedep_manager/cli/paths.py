import os
import click
from rich.console import Console

from onedep_manager.cli.common import ConsolePrinter
from onedep_manager.config import Config
from onedep_manager.packages import get_package

from wwpdb.io.locator.PathInfo import PathInfo, ChemRefPathInfo


@click.group(name="paths", help="Get common OneDep paths")
def paths_group():
    """`paths` command group"""


@paths_group.command(name="get", help="Get the current paths")
@click.argument("type")
@click.argument("identifier")
@click.option("-i", "--site", "site", help="wwPDB site ID (e.g. WWPDB_DEPLOY_TEST_RU). Defaults to the current site.")
def get(type_, identifier, site):
    """`get` command handler
    If no error happens, this must return the path only.
    """
    c = Console()
    printer = ConsolePrinter(console=c)
    config = Config()
    pathinfo = PathInfo()
    ccdpathinfo = ChemRefPathInfo()

    if type_ not in ('tempdep', 'deposit', 'archive', 'upload', 'pickles', 'wfinst', 'session', 'ccid', 'package', 'wfxml', 'tool'):
        printer.error(f"Invalid path type: {type_}\nValid types are: tempdep, deposit, archive, upload, wfinst, session, ccid, package, wfxml, tool")
        return

    if type_ == 'tempdep':
        print(pathinfo.getTempDepPath(dataSetId=identifier))
    
    if type_ == 'deposit':
        print(pathinfo.getDepositPath(dataSetId=identifier))

    if type_ == 'archive':
        print(pathinfo.getArchivePath(dataSetId=identifier))
    
    if type_ == 'upload':
        deposit_path = config.from_site("SITE_ARCHIVE_STORAGE_PATH") # is there a better way to get this?
        print(os.path.join(deposit_path, "temp_files", "deposition_uploads", identifier))
    
    if type_ == 'pickles':
        deposit_path = config.from_site("SITE_ARCHIVE_STORAGE_PATH") # is there a better way to get this?
        print(os.path.join(deposit_path, "temp_files", "deposition-v-200", identifier))

    if type_ == 'wfinst':
        dep_id = identifier.split(":")[0]
        wf_instance = identifier.split(":")[1]
        print(pathinfo.getInstancePath(dataSetId=dep_id, wfInstanceId=wf_instance))

    if type_ == 'session':
        print(pathinfo.getDirPath(dataSetId="", fileSource="session"))

    if type_ == 'ccid':
        print(ccdpathinfo.getFilePath(dataSetId=identifier))

    if type_ == 'package':
        print(get_package(identifier).path)

    if type_ == 'wfxml':
        print(os.path.join(config.from_site("SITE_WF_XML_PATH"), f"{identifier}.xml"))

    if type_ == 'tool':
        print("Not implemented yet")
