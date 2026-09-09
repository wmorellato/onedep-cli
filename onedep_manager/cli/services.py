import click
from rich import console

from onedep_manager.services import LocalDispatcher, RemoteDispatcher
from onedep_manager.cli.common import ConsolePrinter, get_config


@click.group(name="services", help="Manage OneDep services")
def services_group():
    """`services` command group"""


@services_group.command(name="start", help="Start the service on all registered services or locally only.")
@click.argument("service")
@click.option("-l", "--local", "local", is_flag=True, default=False, help="If set, perform operations only on the current host.")
@click.pass_context
def start(ctx, service, local):
    """`start` command handler"""
    config = get_config(ctx)
    c = console.Console()
    printer = ConsolePrinter(console=c)

    if local:
        printer.info(f"Starting {service} locally")
        dispatcher = LocalDispatcher(config=config)
    else:
        printer.info(f"Starting {service} on all registered hosts")
        dispatcher = RemoteDispatcher(config=config)

    try:
        status = dispatcher.start_service(service)
    except Exception as e:
        printer.error(f"Could not start service {service}: {e}")
        return

    rows = []
    for s in status:
        rows.append([s.hostname, str(s.status)])

    printer.table(header=["Hostname", "Status"], data=rows)


@services_group.command(name="stop", help="Stop the service on all registered services or locally only.")
@click.argument("service")
@click.option("-f", "--force", "force", is_flag=True, default=False, help="If set, will forcefully kill services' processes.")
@click.option("-l", "--local", "local", is_flag=True, default=False, help="If set, perform operations only on the current host.")
@click.pass_context
def stop(ctx, service, force, local):
    """`stop` command handler"""
    config = get_config(ctx)
    c = console.Console()
    printer = ConsolePrinter(console=c)

    if local:
        printer.info(f"Stopping local instance of {service}")
        dispatcher = LocalDispatcher(config=config)
    else:
        printer.info(f"Stopping {service} on all registered hosts")
        dispatcher = RemoteDispatcher(config=config)

    try:
        status = dispatcher.stop_service(service)
    except Exception as e:
        printer.error(f"Could not stop service {service}: {e}")
        return

    rows = []
    for s in status:
        rows.append([s.hostname, str(s.status)])

    printer.table(header=["Hostname", "Status"], data=rows)


@services_group.command(name="restart", help="Restart the service on all registered services or locally only.")
@click.argument("service")
@click.option("-f", "--force", "force", is_flag=True, default=False, help="If set, will forcefully kill services' processes.")
@click.option("-l", "--local", "local", is_flag=True, default=False, help="If set, perform operations only on the current host.")
@click.pass_context
def restart(ctx, service, force, local):
    """`restart` command handler"""
    config = get_config(ctx)
    c = console.Console()
    printer = ConsolePrinter(console=c)

    if local:
        printer.info(f"Restarting local instance of {service}")
        dispatcher = LocalDispatcher(config=config)
    else:
        printer.info(f"Restarting {service} on all registered hosts")
        dispatcher = RemoteDispatcher(config=config)

    try:
        status = dispatcher.restart_service(service)
    except Exception as e:
        printer.error(f"Could not restart service {service}: {e}")
        return

    rows = []
    for s in status:
        rows.append([s.hostname, str(s.status)])

    printer.table(header=["Hostname", "Status"], data=rows)


@services_group.command(name="status", help="Check the status of a service on all registered services or locally only.")
@click.argument("service")
@click.option("-l", "--local", "local", is_flag=True, default=False, help="If set, perform operations only on the current host.")
@click.pass_context
def status(ctx, service, local):
    """`status` command handler"""
    config = get_config(ctx)
    c = console.Console()
    printer = ConsolePrinter(console=c)

    if local:
        printer.info(f"Checking status of local instance of {service}")
        dispatcher = LocalDispatcher(config=config)
    else:
        printer.info(f"Checking status of {service} on all registered hosts")
        dispatcher = RemoteDispatcher(config=config)

    try:
        status = dispatcher.get_status(service)
    except Exception as e:
        printer.error(f"Could not get status of service {service}: {e}")
        return

    rows = []
    for s in status:
        rows.append([s.hostname, str(s.status)])

    printer.table(header=["Hostname", "Status"], data=rows)
