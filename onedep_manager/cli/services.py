import click


@click.group(name="services", help="Manage OneDep services")
def services_group():
    """`services` command group"""


@services_group.command(name="start", help="Start the service on all registered services or locally only.")
@click.argument("service")
@click.option("-l", "--local", "local", help="If set, perform operations only on the current host.")
def start(service, local):
    """`start` command handler"""
    


@services_group.command(name="restart", help="Restart the service on all registered services or locally only.")
@click.argument("service")
@click.option("-f", "--force", "force", help="If set, will forcefully kill services' processes.")
@click.option("-l", "--local", "local", help="If set, perform operations only on the current host.")
def restart(service, force, local):
    """`restart` command handler"""


@services_group.command(name="stop", help="Stop the service on all registered services or locally only.")
@click.argument("service")
@click.option("-f", "--force", "force", help="If set, will forcefully kill services' processes.")
@click.option("-l", "--local", "local", help="If set, perform operations only on the current host.")
def stop(service, force, local):
    """`stop` command handler"""


@services_group.command(name="status", help="Check the status of a service on all registered services or locally only.")
@click.argument("service")
@click.option("-l", "--local", "local", help="If set, perform operations only on the current host.")
def status(service, local):
    """`status` command handler"""
