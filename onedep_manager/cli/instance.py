import click


@click.group(name="instance", help="Manage the current OneDep instance")
def instance_group():
    """`instance` command group"""


@instance_group.command(name="install", help="Install a new OneDep instance")
def install():
    """`install` command handler"""


@instance_group.command(name="update", help="Update to the newest version")
def update():
    """`update` command handler"""


@instance_group.command(name="status", help="Get a full report of the current instance")
def status():
    """`status` command handler"""


