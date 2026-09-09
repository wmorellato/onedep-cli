import click
import cmd2

from onedep_manager.shell.bridging import bridge_click_group


@click.group(name="demo", help="Demo command group")
def demo_group():
    pass


@demo_group.command(name="greet")
@click.argument("who")
def greet(who):
    click.echo(f"hello {who}")


@demo_group.command(name="boom")
def boom():
    raise click.ClickException("something went wrong")


def _run(shell, line):
    shell.onecmd_plus_hooks(line)


def test_bridged_group_command_runs(capsys):
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    _run(shell, "demo greet world")

    assert "hello world" in capsys.readouterr().out


def test_bridged_group_click_exception_is_shown_not_raised(capsys):
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    _run(shell, "demo boom")  # must not raise

    assert "something went wrong" in capsys.readouterr().err


def test_bridged_command_gets_docstring_from_group_help():
    shell = cmd2.Cmd()
    bridge_click_group(shell, demo_group, ctx_obj=None)

    assert shell.do_demo.__doc__ == "Demo command group"


def test_bridge_passes_ctx_obj_through():
    seen = {}

    @click.group(name="capture")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    shell = cmd2.Cmd()
    sentinel = object()
    bridge_click_group(shell, capture_group, ctx_obj=sentinel)

    _run(shell, "capture noop")

    assert seen["obj"] is sentinel
