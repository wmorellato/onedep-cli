import click


def invoke_click_group(group: click.Group, args: list, ctx_obj=None) -> None:
    """Run `group` with `args`, handling Click's own exit/error paths.

    Delegates to the group's own main() with standalone_mode disabled, so
    it never calls sys.exit and Click errors are shown (not raised)
    instead of propagating.
    """
    try:
        group.main(args=args, prog_name=group.name, obj=ctx_obj, standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
    except SystemExit:
        pass
