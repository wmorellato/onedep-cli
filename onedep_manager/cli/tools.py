import click


def _not_implemented(command_name):
    click.echo(f"'tools {command_name}' is not implemented yet.", err=True)
    raise SystemExit(1)


@click.group(name="tools", help="Manage OneDep binary toolset")
def tools_group():
    """`tools` command group"""


@tools_group.command(name="build", help="(not yet implemented) Build a binary tool")
@click.argument("package")
def build(package):
    """`build` command handler"""
    _not_implemented("build")


@tools_group.command(name="status", help="(not yet implemented) Check the status of a binary tool")
@click.argument("package")
def status(package):
    """`status` command handler"""
    _not_implemented("status")


@tools_group.command(name="download", help="(not yet implemented) Download a binary tool")
@click.argument("package")
def download(package):
    """`download` command handler"""
    _not_implemented("download")
