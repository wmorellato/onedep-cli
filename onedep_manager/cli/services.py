import click
import logging

from onedep_manager.services.dispatcher import LocalDispatcher, RemoteDispatcher
from onedep_manager.cli.common import ConsolePrinter
from onedep_manager.config import Config


@click.group(name="services", help="Manage OneDep services")
def services_group():
    """`services` command group"""


@services_group.command(name="start", help="Start the service on all registered services or locally only.")
@click.argument("service")
@click.option("-l", "--local", "local", is_flag=True, default=False, help="If set, perform operations only on the current host.")
def start(service, local):
    """`start` command handler"""
    config = Config()

    if local:
        logging.info("Starting service locally")
        dispatcher = LocalDispatcher(config=config)
    else:
        dispatcher = RemoteDispatcher(config=config)

    try:
        status = dispatcher.start_service(service)
    except Exception as e:
        logging.error("Could not start service", exc_info=True)
        click.echo(f"Could not start service {service}: {e}")
        return

    rows = []
    for s in status:
        rows.append([s.hostname, str(s.status)])

    ConsolePrinter().table(header=["Hostname", "Status"], data=rows)


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
