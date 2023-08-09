import click


@click.group(name="packages", help="Manage OneDep Python packages")
def packages_group():
    """`packages` command group"""


@packages_group.command(name="upgrade", help="Foobar")
@click.argument("package")
def upgrade(package):
    """`upgrade` command handler"""


@packages_group.command(name="checkout", help="Foobar")
@click.argument("package")
def checkout(package):
    """`checkout` command handler"""


@packages_group.command(name="status", help="Foobar")
@click.argument("package")
def status(package):
    """`status` command handler"""


