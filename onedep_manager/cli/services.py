import click


@click.group(name="services", help="Manage OneDep services")
def services_group():
    """`services` command group"""


@services_group.command(name="list", help="Foobar")
@click.argument("service")
def list(service):
    """`list` command handler"""


@services_group.command(name="start", help="Foobar")
@click.argument("service")
def start(service):
    """`start` command handler"""


@services_group.command(name="restart", help="Foobar")
@click.argument("service")
def restart(service):
    """`restart` command handler"""


@services_group.command(name="stop", help="Foobar")
@click.argument("service")
def stop(service):
    """`stop` command handler"""


@services_group.command(name="status", help="Foobar")
@click.argument("service")
def status(service):
    """`status` command handler"""


