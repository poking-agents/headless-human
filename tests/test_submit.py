from __future__ import annotations
import sys

import pathlib
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

class CheckoutGitTestScenario(BaseModel):
    git_status_mocked_output: str = ""
    internet_permissions: list[str] = []
    git_push_result: tuple[int, str] | None = None # (exit_code, output_message)
    expected_prompts_start: list[str] = []

@pytest.fixture(autouse=True)
def fixture_clear_modules():
    if "src.submit" in sys.modules:
        del sys.modules["src.submit"]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["internet"],
                git_push_result=(0, "Everything up-to-date"),
                expected_prompts_start=[],
            ),
            id="no_changes_with_internet",
            
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=[],
                git_push_result=None,
                expected_prompts_start=[
                "Since this task is running on a container with no internet access,"
                ],
            ),
            id="no_changes_without_internet",
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                git_status_mocked_output="M modified_file.txt",
                internet_permissions=[],
                git_push_result=None,
                expected_prompts_start=[
                "Are you sure you want to continue?",
                "Since this task is running on a container with no internet access,",
                ],
            ),
            id="uncommitted_changes_confirmed",
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["internet"],
                git_push_result=(1, "Failed to push: remote error"),
                expected_prompts_start=["Are you sure you want to continue?"],
            ),
            id="push_failure_confirmed",
        ),
    ]
)
async def test_check_git_repo(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
    scenario: CheckoutGitTestScenario,
):
    # Mock settings.get_settings (before importing submit)
    mock_settings = mocker.Mock(permissions=scenario.internet_permissions) # TODO: Is this right?
    mocker.patch("src.settings.get_settings", return_value=mock_settings, autospec=True)

    from src.submit import _check_git_repo

    # Mock git status (subprocess.create_subprocess_exec)
    async def mock_subprocess_exec(*args, **kwargs):
        process_mock = mocker.AsyncMock()
        process_mock.communicate.return_value = (scenario.git_status_mocked_output.encode(), None)
        process_mock.wait.return_value = 0
        return process_mock
    mocker.patch("asyncio.subprocess.create_subprocess_exec", side_effect=mock_subprocess_exec, autospec=True)

    # Mock git push if needed
    if scenario.git_push_result is not None:
        async def mock_git_push(repo_dir):
            return scenario.git_push_result
        mocker.patch("src.submit._git_push", side_effect=mock_git_push, autospec=True)

    # Mock click.confirm and track calls
    mock_confirm = mocker.patch("click.confirm", return_value=True, autospec=True)

    # Run the function
    repo_dir = pathlib.Path("/fake/path")
    await _check_git_repo(repo_dir)

    # Verify the confirmation prompts
    actual_prompts = [call.args[0] for call in mock_confirm.call_args_list]
    assert all(actual_prompt.startswith(expected_prompt) for actual_prompt, expected_prompt in zip(actual_prompts, scenario.expected_prompts_start))

    # Verify expected output messages
    captured = capsys.readouterr()
    
    # Did git status show uncommitted changes?
    if scenario.git_status_mocked_output:
        assert "Uncommitted changes in" in captured.out
        assert scenario.git_status_mocked_output in captured.out
    else:
        assert "No uncommitted changes in" in captured.out

    if scenario.git_push_result is not None:
        if scenario.git_push_result[0] == 0:
            assert "Successfully pushed to git remote." in captured.out
        else:
            assert "Failed to push to git remote:" in captured.out
            assert scenario.git_push_result[1] in captured.out
