from __future__ import annotations

import json
import pathlib
import textwrap
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="env_setup")
def fixture_env_setup(mocker: MockerFixture, tmp_path: pathlib.Path, mock_hooks):
    from src.clock import ClockStatus

    mock_run_info = {
        "task": {"instructions": "test instructions", "scoring": {"intermediate": True}}
    }

    info_file = tmp_path / "run_info.json"
    info_file.write_text(json.dumps(mock_run_info))
    mocker.patch("src.human_setup.RUN_INFO_FILE", info_file)

    welcome_file = tmp_path / "some" / "path" / "welcome.txt"
    mocker.patch("src.human_setup.WELCOME_MESSAGE_FILE", welcome_file)

    mocker.patch("src.clock.get_status", return_value=ClockStatus.RUNNING)


@pytest.mark.parametrize("shell_env", ["/bin/bash", "/usr/bin/zsh", "bla/bla/bla"])
@pytest.mark.asyncio
async def test_get_shell_path_from_env(
    mocker: MockerFixture, shell_env: str, env_setup
):
    from src.human_setup import _get_shell_path

    mocker.patch.dict("os.environ", {"SHELL": shell_env})
    assert await _get_shell_path() == pathlib.Path(shell_env)


@pytest.mark.asyncio
async def test_get_shell_path_from_proc(mocker: MockerFixture):
    from src.human_setup import _get_shell_path

    mock_file = AsyncMock()
    mock_file.__aenter__.return_value.read = AsyncMock(return_value="zsh")
    mocker.patch.dict("os.environ", {"SHELL": ""})
    mocker.patch("os.getppid", return_value=12345)
    mocker.patch("aiofiles.open", return_value=mock_file)
    assert await _get_shell_path() == pathlib.Path("zsh")


@pytest.mark.asyncio
async def test_get_shell_path_from_python(mocker: MockerFixture):
    from src.human_setup import _get_shell_path

    mock_file = AsyncMock()
    mock_file.__aenter__.return_value.read = AsyncMock(return_value="zsh")
    mocker.patch.dict("os.environ", {"SHELL": ""})
    mocker.patch("os.getppid", return_value=12345)
    mocker.patch("aiofiles.open", side_effect=FileNotFoundError())

    mocker.patch("sys.executable", "/usr/bin/python")
    assert await _get_shell_path() == pathlib.Path("/usr/bin/python")


@pytest.mark.asyncio
async def test_get_shell_path_no_getppid(mocker: MockerFixture):
    from src.human_setup import _get_shell_path

    mocker.patch.dict("os.environ", {"SHELL": ""})
    mocker.patch("builtins.hasattr", return_value=False)
    mocker.patch("sys.executable", "/usr/bin/python")
    assert await _get_shell_path() == pathlib.Path("/usr/bin/python")


@pytest.mark.asyncio
async def test_get_shell_path_failure(mocker: MockerFixture):
    from src.human_setup import _get_shell_path

    mocker.patch.dict("os.environ", {"SHELL": ""})
    mocker.patch("builtins.hasattr", return_value=False)
    mocker.patch("sys.executable", "/usr/bin/unknown")
    with pytest.raises(RuntimeError, match="Could not determine shell path"):
        await _get_shell_path()


@pytest.mark.parametrize(
    "shell_name,expected",
    [
        ("zsh", pathlib.Path.home() / ".zshrc"),
        ("zsh-5.8", pathlib.Path.home() / ".zshrc"),
        ("bash", pathlib.Path.home() / ".bashrc"),
        ("BaSh-123", pathlib.Path.home() / ".bashrc"),
    ],
)
def test_get_shell_config_file_supported(shell_name: str, expected: pathlib.Path):
    from src.human_setup import _get_shell_config_file

    assert _get_shell_config_file(pathlib.Path(f"/usr/bin/{shell_name}")) == expected


@pytest.mark.parametrize(
    "shell_name",
    [
        "python",
        "python3",
        "ipython",
    ],
)
def test_get_shell_config_file_python(shell_name: str):
    from src.human_setup import _get_shell_config_file

    assert _get_shell_config_file(pathlib.Path(f"/usr/bin/{shell_name}")) is None


@pytest.mark.parametrize(
    "shell_name",
    [
        "fish",
        "csh",
        "tcsh",
        "unknown",
    ],
)
def test_get_shell_config_file_unsupported(shell_name: str):
    from src.human_setup import _get_shell_config_file

    with pytest.raises(
        NotImplementedError, match=f"Cannot configure terminal for {shell_name}"
    ):
        _get_shell_config_file(pathlib.Path(f"/usr/bin/{shell_name}"))


@pytest.mark.asyncio
async def test_get_welcome_message():
    from src.human_setup import (
        INSTRUCTIONS_FILE,
        WELCOME_MESSAGE_FILE,
        _get_welcome_message,
    )

    commands = {
        "clock": "Start/stop timer",
        "submit": "Submit work",
    }
    instructions = "Test instructions"

    welcome_saved, welcome_unsaved, instructions_desc = await _get_welcome_message(
        commands, instructions
    )

    assert "Test instructions" in instructions_desc
    assert str(INSTRUCTIONS_FILE) in instructions_desc
    assert "`clock`: Start/stop timer" in welcome_saved
    assert "`submit`: Submit work" in welcome_saved
    assert str(WELCOME_MESSAGE_FILE) in welcome_unsaved
    assert "Please don't modify any files" in welcome_saved
    assert "WELCOME TO YOUR METR TASK" in welcome_saved


def test_get_conditional_run_command():
    from src.human_setup import HelperCommand, get_conditional_run_command

    expected = "[ -z ${SETUP_DONE} ] && $(type -t setup > /dev/null) && setup && export SETUP_DONE=1"
    assert get_conditional_run_command("SETUP_DONE", HelperCommand.setup) == expected


@pytest.mark.asyncio
async def test_create_profile_file(tmp_path: pathlib.Path):
    from src.human_setup import HelperCommand, create_profile_file

    profile_file = tmp_path / "profile.sh"
    env = {"TEST_VAR": "test_value", "PATH": "/usr/bin"}

    await create_profile_file(
        intermediate_scoring=True,
        with_recording=True,
        env=env,
        profile_file=profile_file,
    )

    content = profile_file.read_text()

    # Check environment exports
    assert "export TEST_VAR='test_value'" in content
    assert "export PATH='/usr/bin'" in content
    assert "export SHELL" in content

    # Check aliases for all commands
    for command in HelperCommand:
        assert f"alias {command.name}=" in content

    # Check conditional commands
    assert "METR_BASELINE_SETUP_COMPLETE" in content
    assert "METR_RECORDING_STARTED" in content


@pytest.mark.asyncio
async def test_create_profile_file_no_scoring_no_recording(tmp_path: pathlib.Path):
    from src.human_setup import create_profile_file

    profile_file = tmp_path / "profile.sh"

    await create_profile_file(
        intermediate_scoring=False,
        with_recording=False,
        env={},
        profile_file=profile_file,
    )

    content = profile_file.read_text()

    # Check scoring commands are not included
    assert "score" not in content
    assert "score_log" not in content

    # Check recording command is not included
    assert "record" not in content
    assert "METR_RECORDING_STARTED" not in content

    # Core commands should still be there
    assert "alias clock=" in content
    assert "alias submit=" in content


@pytest.mark.asyncio
async def test_ensure_sourced_new_entry(tmp_path: pathlib.Path):
    from src.human_setup import ensure_sourced

    shell_config = tmp_path / ".zshrc"
    profile_file = tmp_path / "profile.sh"

    # Test with empty config file
    sourced = await ensure_sourced(shell_config, profile_file)
    assert shell_config.parent.exists()
    assert not sourced
    assert f"\n[[ $- == *i* ]] && . {profile_file}\n" in shell_config.read_text()


@pytest.mark.asyncio
async def test_ensure_sourced_already_exists(tmp_path: pathlib.Path):
    from src.human_setup import ensure_sourced

    shell_config = tmp_path / ".zshrc"
    profile_file = tmp_path / "profile.sh"

    # Create config with existing source command
    shell_config.write_text(f"some content\n. {profile_file}\nmore content")

    assert await ensure_sourced(shell_config, profile_file)
    assert shell_config.parent.exists()
    assert shell_config.read_text() == f"some content\n. {profile_file}\nmore content"


@pytest.mark.parametrize(
    "clock_status, expected_echo_count",
    [
        ("running", 3),
        ("stopped", 2),
    ],
)
@pytest.mark.asyncio
async def test_show_welcome_message_clock_running(
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
    mock_hooks,
    clock_status: str,
    expected_echo_count: int,
):
    from src.human_setup import clock, show_welcome_message

    mock_run_info = {
        "task": {"instructions": "test instructions", "scoring": {"intermediate": True}}
    }

    info_file = tmp_path / "run_info.json"
    info_file.write_text(json.dumps(mock_run_info))
    mocker.patch("src.human_setup.RUN_INFO_FILE", info_file)

    welcome_file = tmp_path / "some" / "path" / "welcome.txt"
    mocker.patch("src.human_setup.WELCOME_MESSAGE_FILE", welcome_file)

    mocker.patch(
        "src.clock.get_status", return_value=clock.ClockStatus(clock_status.upper())
    )
    mock_click_echo = mocker.patch("click.echo", autospec=True)

    status, instructions = await show_welcome_message()

    assert status == clock.ClockStatus(clock_status.upper())
    assert (
        instructions
        == textwrap.dedent("""
        =================================================================================
        Task instructions are at /home/agent/instructions.txt, and are also displayed below.
        =================================================================================
        test instructions
    """).strip()
    )
    assert welcome_file.exists()
    # Echo should be called with the generic welcome message, the unsaved
    # welcome message, and the instructions if the clock is running
    assert mock_click_echo.call_count == expected_echo_count


@pytest.mark.asyncio
async def test_show_welcome_message_welcome_exists(
    mocker: MockerFixture, tmp_path: pathlib.Path, mock_hooks
):
    from src.human_setup import show_welcome_message

    mock_run_info = {
        "task": {"instructions": "test instructions", "scoring": {"intermediate": True}}
    }

    info_file = tmp_path / "run_info.json"
    info_file.write_text(json.dumps(mock_run_info))
    mocker.patch("src.human_setup.RUN_INFO_FILE", info_file)

    welcome_file = tmp_path / "welcome.txt"
    mocker.patch("src.human_setup.WELCOME_MESSAGE_FILE", welcome_file)
    welcome_file.write_text("Welcome message")

    await show_welcome_message()

    assert welcome_file.exists()
    assert welcome_file.read_text() == "Welcome message"


@pytest.mark.asyncio
async def test_check_started_already_running(mocker: MockerFixture):
    from src.human_setup import check_started, clock

    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus.RUNNING)
    mock_click_echo = mocker.patch("click.echo", autospec=True)
    assert await check_started(clock.ClockStatus.RUNNING, "test instructions")
    assert mock_click_echo.call_count == 0


@pytest.mark.asyncio
async def test_check_started_starts_running(mocker: MockerFixture):
    from src.human_setup import check_started, clock

    mocker.patch("src.clock.clock", return_value=clock.ClockStatus.RUNNING)
    mock_click_echo = mocker.patch("click.echo", autospec=True)
    assert await check_started(clock.ClockStatus.STOPPED, "test instructions")
    mock_click_echo.assert_called_once_with("test instructions")


@pytest.mark.asyncio
async def test_check_started_stays_stopped(mocker: MockerFixture):
    from src.human_setup import check_started, clock

    mocker.patch("src.clock.clock", return_value=clock.ClockStatus.STOPPED)
    mock_click_echo = mocker.patch("click.echo", autospec=True)
    assert not await check_started(clock.ClockStatus.STOPPED, "test instructions")
    assert mock_click_echo.call_count == 0


@pytest.mark.asyncio
async def test_main_already_setup(mocker: MockerFixture):
    from src.human_setup import main

    mocker.patch.dict("os.environ", {"METR_BASELINE_SETUP_COMPLETE": "1"})
    assert await main() == 0


@pytest.mark.asyncio
async def test_main_shell_path_error(mocker: MockerFixture, env_setup):
    from src.human_setup import main

    mocker.patch.dict("os.environ", {})
    mocker.patch("src.human_setup._get_shell_path", side_effect=RuntimeError)
    mock_click = mocker.patch("click.echo")

    assert await main() == 1
    mock_click.assert_called_with(
        "Could not determine shell path, skipping profile file sourcing", err=True
    )


@pytest.mark.asyncio
async def test_main_python_shell(mocker: MockerFixture, env_setup):
    from src.human_setup import main

    mocker.patch.dict("os.environ", {})
    mocker.patch(
        "src.human_setup._get_shell_path", return_value=pathlib.Path("/usr/bin/python")
    )
    mock_click = mocker.patch("click.echo")

    assert await main() == 1
    mock_click.assert_called_with(
        "Could not determine shell config file, skipping profile file sourcing",
        err=True,
    )


@pytest.mark.asyncio
async def test_main_needs_source(mocker: MockerFixture, env_setup):
    from src.human_setup import HelperCommand, main

    mocker.patch.dict("os.environ", {})
    mocker.patch(
        "src.human_setup._get_shell_path", return_value=pathlib.Path("/bin/zsh")
    )
    mocker.patch(
        "src.human_setup._get_shell_config_file", return_value=pathlib.Path("~/.zshrc")
    )
    mocker.patch("src.human_setup.is_alias_defined", AsyncMock(return_value=False))
    mocker.patch("src.human_setup.ensure_sourced", AsyncMock(return_value=True))
    mock_click = mocker.patch("click.echo")

    assert await main() == 1

    mock_click.assert_any_call(
        "Please run the following commands to complete the setup and start the task:"
    )
    mock_click.assert_any_call("\n  source ~/.zshrc")
    mock_click.assert_any_call(f"  {HelperCommand.clock.name}")


@pytest.mark.asyncio
async def test_main_clock_not_running(mocker: MockerFixture, env_setup):
    from src.human_setup import main

    mocker.patch.dict("os.environ", {})
    mocker.patch(
        "src.human_setup._get_shell_path", return_value=pathlib.Path("/bin/zsh")
    )
    mocker.patch(
        "src.human_setup._get_shell_config_file", return_value=pathlib.Path("~/.zshrc")
    )
    mocker.patch("src.human_setup.is_alias_defined", AsyncMock(return_value=True))
    mocker.patch("src.human_setup.check_started", AsyncMock(return_value=False))

    assert await main() == 1


@pytest.mark.asyncio
async def test_main_success(mocker: MockerFixture, env_setup):
    from src.human_setup import clock, main

    mocker.patch.dict("os.environ", {})
    mocker.patch(
        "src.human_setup._get_shell_path", return_value=pathlib.Path("/bin/zsh")
    )
    mocker.patch("src.human_setup.is_alias_defined", AsyncMock(return_value=True))
    mocker.patch("src.human_setup.check_started", AsyncMock(return_value=True))
    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus.RUNNING)

    assert await main() == 0
