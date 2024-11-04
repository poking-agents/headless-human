from __future__ import annotations

import asyncio
import pathlib
from typing import TYPE_CHECKING

import click
import pytest
import pyhooks

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

@pytest.fixture(autouse=True)
def fixture_run_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_URL", "http://localhost:8000")
    monkeypatch.setenv("RUN_ID", "123")
    monkeypatch.setenv("AGENT_TOKEN", "456")
    monkeypatch.setenv("AGENT_BRANCH_NUMBER", "0")
    monkeypatch.setenv("TASK_ID", "task/test")
    monkeypatch.setenv("PYHOOKS_DEBUG", "0")

@pytest.fixture(autouse=True)
def clear_modules():
    import sys
    if "src.submit" in sys.modules:
        del sys.modules["src.submit"]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scenario", "git_status_mocked_output", "has_internet", "git_push_result", "expected_prompts"),
    [
        (
            "no_changes_with_internet",
            "",
            ["internet"],
            (0, "Everything up-to-date"),
            [],  # No prompts expected
        ),
        (
            "no_changes_without_internet",
            "",
            [],
            None,
            ["Since this task is running on a container with no internet access, please clone the repository to your local machine and push your changes from there to github, and only confirm once this is done."],
        ),
        (
            "uncommitted_changes_confirmed",
            "M modified_file.txt",
            [],
            None,
            [
                "Are you sure you want to continue?",
                "Since this task is running on a container with no internet access, please clone the repository to your local machine and push your changes from there to github, and only confirm once this is done.",
            ],
        ),
        (
            "push_failure_confirmed",
            "",
            ["internet"],
            (1, "Failed to push: remote error"),
            ["Are you sure you want to continue?"],  # Expect push failure prompt
        ),
    ]
)
async def test_check_git_repo(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
    scenario: str,
    git_status_mocked_output: str,
    has_internet: list[str],
    git_push_result: tuple[int, str] | None,
    expected_prompts: list[str],
):
    # Mock HOOKS.getTask (before importing submit)
    mock_hooks = mocker.Mock()
    mock_task = mocker.Mock(permissions=has_internet)
    mock_hooks.getTask = mocker.AsyncMock(return_value=mock_task)
    mocker.patch("src.settings.HOOKS", mock_hooks)

    from src.submit import _check_git_repo

    # Mock git status (subprocess.create_subprocess_exec)
    async def mock_subprocess_exec(*args, **kwargs):
        process_mock = mocker.AsyncMock()
        process_mock.communicate.return_value = (git_status_mocked_output.encode(), None)
        process_mock.wait.return_value = 0
        return process_mock
    mocker.patch("asyncio.subprocess.create_subprocess_exec", side_effect=mock_subprocess_exec)

    # Mock git push if needed
    if git_push_result is not None:
        async def mock_git_push(repo_dir):
            return git_push_result
        mocker.patch("src.submit._git_push", side_effect=mock_git_push)

    # Mock click.confirm and track calls
    mock_confirm = mocker.patch("click.confirm", return_value=True)

    # Run the function
    repo_dir = pathlib.Path("/fake/path")
    await _check_git_repo(repo_dir)

    # Verify the confirmation prompts
    actual_prompts = [call.args[0] for call in mock_confirm.call_args_list]
    assert actual_prompts == expected_prompts

    # Verify expected output messages
    captured = capsys.readouterr()
    
    # Did git status show uncommitted changes?
    if git_status_mocked_output:
        assert "Uncommitted changes in" in captured.out
        assert git_status_mocked_output in captured.out
    else:
        assert "No uncommitted changes in" in captured.out

    if git_push_result is not None:
        if git_push_result[0] == 0:
            assert "Successfully pushed to git remote." in captured.out
        else:
            assert "Failed to push to git remote:" in captured.out
            assert git_push_result[1] in captured.out
