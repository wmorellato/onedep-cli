import shlex

import click


def bridge_click_group(shell, group: click.Group, ctx_obj=None) -> None:
    """Register `group` as a top-level `do_<group.name>` command on `shell`.

    Delegates straight to the group's own `main()` with standalone_mode
    disabled, so it never calls sys.exit and Click errors are printed
    (not raised) instead of crashing the shell loop.
    """

    def handler(arg) -> None:
        args = shlex.split(str(arg))
        try:
            group.main(args=args, prog_name=group.name, obj=ctx_obj, standalone_mode=False)
        except click.ClickException as exc:
            exc.show()
        except SystemExit:
            pass

    handler.__doc__ = group.help or f"Run {group.name} commands"
    setattr(shell, f"do_{group.name}", handler)
