from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

class CheckoutGitTestScenario(BaseModel):
    git_status_mocked_output: str = ""
    internet_permissions: list[str] = []
    git_push_result: tuple[int, str] | None = None # (exit_code, output_message)
    expected_prompts_start: list[str] = []
    expected_output: list[str] = []  # New field for expected output messages

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["full internet"],
                git_push_result=(0, "Everything up-to-date"),
                expected_prompts_start=[],
                expected_output=[
                    "No uncommitted changes in",
                    "Successfully pushed to git remote."
                ],
            ),
            id="no_changes_with_internet",
            
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["limited internet"],
                git_push_result=None,
                expected_prompts_start=[
                "Since this task is running on a container with no internet access,"
                ],
                expected_output=[
                    "No uncommitted changes in"
                ],
            ),
            id="no_changes_without_internet",
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                git_status_mocked_output="M modified_file.txt",
                internet_permissions=["limited internet"],
                git_push_result=None,
                expected_prompts_start=[
                "Are you sure you want to continue?",
                "Since this task is running on a container with no internet access,",
                ],
                expected_output=[
                    "Uncommitted changes in",
                    "M modified_file.txt"
                ],
            ),
            id="uncommitted_changes_confirmed",
        ),        
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["full internet"],
                git_push_result=(1, "Failed to push: remote error"),
                expected_prompts_start=["Are you sure you want to continue?"],
                expected_output=[
                    "No uncommitted changes in",
                    "Failed to push to git remote:",
                    "Failed to push: remote error"
                ],
            ),
            id="push_failure_confirmed",
        ),
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=[],  # empty list
                git_push_result=None,
                expected_prompts_start=[
                "Since this task is running on a container with no internet access,"
                ],
                expected_output=[
                    "No uncommitted changes in"
                ],
            ),
            id="empty_permissions_list",
        ),
        pytest.param(
            CheckoutGitTestScenario(
                internet_permissions=["no internet"],  # explicit no internet
                git_push_result=None,
                expected_prompts_start=[
                "Since this task is running on a container with no internet access,"
                ],
                expected_output=[
                    "No uncommitted changes in"
                ],
            ),
            id="explicit_no_internet",
        ),
    ]
)
async def test_check_git_repo(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
    fp: FakeProcess,
    scenario: CheckoutGitTestScenario,
):
    # Mock settings.get_settings to return a dictionary instead of a Mock
    mocker.patch(
        "src.settings.get_settings",
        return_value={"permissions": scenario.internet_permissions},
        autospec=True
    )

    from src.submit import _check_git_repo

    # Mock git status using pytest-subprocess
    fp.register(
        ["git", "status", "--porcelain"],
        stdout=scenario.git_status_mocked_output.encode()
    )

    # Mock git push if needed
    if scenario.git_push_result is not None:
        exit_code, output = scenario.git_push_result
        fp.register(
            ["git", "push"],
            stdout=output.encode(),
            returncode=exit_code
        )

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
    for expected in scenario.expected_output:
        assert expected in captured.out
