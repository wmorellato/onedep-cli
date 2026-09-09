import stat
import textwrap

import pytest

from onedep_manager.shell.scripts import ScriptNotFoundError, ScriptRegistry


def _write_script(directory, name, body, description="", tags=None):
    script_path = directory / name
    script_path.write_text(body)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    sidecar = directory / f"{name}.yaml"
    tags = tags or []
    sidecar.write_text(
        textwrap.dedent(
            f"""
            name: {name}
            description: {description}
            tags: {tags}
            """
        )
    )
    return script_path


def test_list_registered_scripts(tmp_path):
    _write_script(tmp_path, "hello.sh", "#!/bin/sh\necho hi\n", description="says hi", tags=["demo"])

    registry = ScriptRegistry([tmp_path])
    listed = registry.list()

    assert len(listed) == 1
    assert listed[0].name == "hello.sh"
    assert listed[0].description == "says hi"
    assert listed[0].tags == ["demo"]


def test_list_filters_by_tag(tmp_path):
    _write_script(tmp_path, "a.sh", "#!/bin/sh\n", tags=["demo"])
    _write_script(tmp_path, "b.sh", "#!/bin/sh\n", tags=["other"])

    registry = ScriptRegistry([tmp_path])

    assert [s.name for s in registry.list(tag="demo")] == ["a.sh"]
    assert [s.name for s in registry.list(tag="nope")] == []


def test_script_without_sidecar_is_not_registered(tmp_path):
    (tmp_path / "loose.sh").write_text("#!/bin/sh\necho hi\n")

    registry = ScriptRegistry([tmp_path])

    assert registry.list() == []


def test_run_executes_script_and_returns_exit_code(tmp_path, capfd):
    _write_script(tmp_path, "hello.sh", "#!/bin/sh\necho hi\nexit 3\n")

    registry = ScriptRegistry([tmp_path])
    code = registry.run("hello.sh")

    out, _ = capfd.readouterr()
    assert "hi" in out
    assert code == 3


def test_run_passes_arguments(tmp_path, capfd):
    _write_script(tmp_path, "echo_arg.sh", '#!/bin/sh\necho "arg=$1"\n')

    registry = ScriptRegistry([tmp_path])
    registry.run("echo_arg.sh", ["hello"])

    out, _ = capfd.readouterr()
    assert "arg=hello" in out


def test_run_unregistered_script_raises(tmp_path):
    registry = ScriptRegistry([tmp_path])

    with pytest.raises(ScriptNotFoundError):
        registry.run("does-not-exist.sh")


def test_registry_merges_multiple_directories(tmp_path):
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()

    _write_script(builtin_dir, "builtin.sh", "#!/bin/sh\n", tags=["builtin"])
    _write_script(user_dir, "user.sh", "#!/bin/sh\n", tags=["user"])

    registry = ScriptRegistry([builtin_dir, user_dir])

    assert {s.name for s in registry.list()} == {"builtin.sh", "user.sh"}
