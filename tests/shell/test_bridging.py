import click

from onedep_manager.shell.bridging import invoke_click_group


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


def test_invoke_runs_the_command(capsys):
    invoke_click_group(demo_group, ["greet", "world"])

    assert "hello world" in capsys.readouterr().out


def test_invoke_shows_click_exception_instead_of_raising(capsys):
    invoke_click_group(demo_group, ["boom"])  # must not raise

    assert "something went wrong" in capsys.readouterr().err


def test_invoke_passes_ctx_obj_through():
    seen = {}

    @click.group(name="capture")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    sentinel = object()

    invoke_click_group(capture_group, ["noop"], ctx_obj=sentinel)

    assert seen["obj"] is sentinel


def test_invoke_with_no_ctx_obj_defaults_to_none():
    seen = {}

    @click.group(name="capture2")
    @click.pass_context
    def capture_group(ctx):
        seen["obj"] = ctx.obj

    @capture_group.command(name="noop")
    @click.pass_context
    def noop(ctx):
        pass

    invoke_click_group(capture_group, ["noop"])

    assert seen["obj"] is None
