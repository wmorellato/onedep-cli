import click


@click.group(name="tools", help="Manage OneDep binary toolset")
def tools_group():
    """`tools` command group"""


@tools_group.command(name="build", help="Foobar")
@click.argument("package")
def build(package):
    """`build` command handler"""


@tools_group.command(name="status", help="Foobar")
@click.argument("package")
def status(package):
    """`status` command handler"""


@tools_group.command(name="download", help="Foobar")
@click.argument("package")
def download(package):
    """`download` command handler"""


