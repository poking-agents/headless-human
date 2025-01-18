from __future__ import annotations
import pathlib
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType

import click
import pytest


def git_command(
    cwd: pathlib.Path, *args, capture_output=False
) -> tuple[int, str | None]:
    """Execute a git command in the given directory."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=capture_output,
        text=True,
    )
    return result.returncode, result.stdout.strip() if capture_output else None


@pytest.fixture
def git_repo(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Creates a temporary git repo with an initial commit"""
    repo_path = tmp_path / "solution"
    repo_path.mkdir()

    git_command(repo_path, "init", "-b", "main")
    git_command(repo_path, "config", "user.name", "Test User")
    git_command(repo_path, "config", "user.email", "test@example.com")

    # Create and commit an initial file
    initial_file = repo_path / "initial.txt"
    initial_file.write_text("initial content")

    git_command(repo_path, "add", "initial.txt")
    git_command(repo_path, "commit", "-m", "Initial commit")

    # Get current branch name
    returncode, branch = git_command(
        repo_path, "branch", "--show-current", capture_output=True
    )
    assert returncode == 0

    return repo_path, branch or "main"


@pytest.fixture
def remote_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Creates a bare git repository to serve as remote"""
    remote_path = tmp_path / "remote"
    remote_path.mkdir()
    assert git_command(remote_path, "init", "--bare", "-b", "main") == (0, None)
    return remote_path


@pytest.fixture
def git_repo_with_remote(
    git_repo: tuple[pathlib.Path, str], remote_repo: pathlib.Path
) -> tuple[pathlib.Path, str]:
    """Creates a git repo with a remote configured"""
    repo, branch = git_repo
    returncode, _ = git_command(repo, "remote", "add", "origin", str(remote_repo))
    assert returncode == 0

    # Set up tracking branch
    returncode, _ = git_command(repo, "push", "-u", "origin", branch)
    assert returncode == 0

    return repo, branch


@pytest.mark.asyncio
async def test_create_submission_commit_adds_empty_commit(
    git_repo: tuple[pathlib.Path, str],
):
    from src.submit import _create_submission_commit

    repo, _branch = git_repo

    # Create an uncommitted change
    test_file = repo / "test.txt"
    test_file.write_text("test content")
    git_command(repo, "add", "test.txt")

    await _create_submission_commit(repo)

    # Verify the submission commit was created
    commit_message = git_command(repo, "log", "-1", "--pretty=%B", capture_output=True)
    assert commit_message == (0, "SUBMISSION")

    # Verify the uncommitted changes are still present
    status_code, status = git_command(
        repo, "status", "--porcelain", capture_output=True
    )
    assert status_code == 0
    assert status and "A  test.txt" in status


@pytest.mark.asyncio
async def test_create_submission_commit_with_untracked_files(
    git_repo: tuple[pathlib.Path, str],
):
    from src.submit import _create_submission_commit

    repo, _branch = git_repo

    # Create an untracked file
    test_file = repo / "untracked.txt"
    test_file.write_text("untracked content")

    await _create_submission_commit(repo)

    # Verify the submission commit was created
    commit_message = git_command(repo, "log", "-1", "--pretty=%B", capture_output=True)
    assert commit_message == (0, "SUBMISSION")

    # Verify the untracked file is still present
    status_code, status = git_command(
        repo, "status", "--porcelain", capture_output=True
    )
    assert status_code == 0
    assert status and "?? untracked.txt" in status


@pytest.mark.asyncio
async def test_git_push_successful(git_repo_with_remote: tuple[pathlib.Path, str]):
    from src.submit import _git_push

    repo, _branch = git_repo_with_remote

    return_code, output = await _git_push(repo)
    assert return_code == 0, output
    assert output and "Everything up-to-date" in output


@pytest.mark.asyncio
async def test_git_push_fails_with_no_remote(git_repo: tuple[pathlib.Path, str]):
    from src.submit import _git_push

    repo, _branch = git_repo

    return_code, output = await _git_push(repo)
    assert return_code != 0, output
    assert "No configured push destination" in output


@pytest.mark.asyncio
async def test_git_push_with_conflicts(
    git_repo_with_remote: tuple[pathlib.Path, str], remote_repo: pathlib.Path
):
    """Test push failing when remote has diverged"""
    from src.submit import _git_push

    repo, _ = git_repo_with_remote

    # Clone the remote to create divergent history
    remote = remote_repo
    other_clone = remote.parent / "other_clone"
    git_command(remote.parent, "clone", str(remote), "other_clone")

    # Create conflicting commit in other clone
    conflict_file = other_clone / "conflict.txt"
    conflict_file.write_text("conflict content")
    git_command(other_clone, "config", "user.name", "Test User")
    git_command(other_clone, "config", "user.email", "test@example.com")
    git_command(other_clone, "add", "conflict.txt")
    git_command(other_clone, "commit", "-m", "Conflicting commit")
    git_command(other_clone, "push")

    # Create local commit
    local_file = repo / "local.txt"
    local_file.write_text("local content")
    git_command(repo, "add", "local.txt")
    git_command(repo, "commit", "-m", "Local commit")

    # Push should now fail
    return_code, output = await _git_push(repo)
    assert return_code != 0
    assert "[rejected]" in output or "failed to push" in output


@pytest.mark.asyncio
async def test_check_git_repo_clean(
    git_repo_with_remote: tuple[pathlib.Path, str], mocker: MockerFixture
):
    from src.submit import _check_git_repo

    repo, _ = git_repo_with_remote

    echo_mock = mocker.patch("click.echo", autospec=True)
    mocker.patch("click.confirm", return_value=True, autospec=True)
    await _check_git_repo(repo)

    echo_mock.assert_any_call(f"No uncommitted changes in {repo}")
    echo_mock.assert_any_call("Successfully pushed to git remote.")

    # Make sure the submission commit was created
    assert git_command(repo, "log", "-1", "--pretty=%B", capture_output=True) == (
        0,
        "SUBMISSION",
    )


@pytest.mark.asyncio
async def test_check_git_repo_with_changes(
    git_repo_with_remote: tuple[pathlib.Path, str], mocker: MockerFixture
):
    from src.submit import _check_git_repo

    repo, _ = git_repo_with_remote

    # Create uncommitted change
    (repo / "new.txt").write_text("new content")
    git_command(repo, "add", "new.txt")

    echo_mock = mocker.patch("click.echo")

    mocker.patch("click.confirm", return_value=True, autospec=True)
    await _check_git_repo(repo)

    echo_mock.assert_any_call(f"Uncommitted changes in {repo}:")
    echo_mock.assert_any_call("Successfully pushed to git remote.")

    # Make sure the submission commit was created
    assert git_command(repo, "log", "-1", "--pretty=%B", capture_output=True) == (
        0,
        "SUBMISSION",
    )


@pytest.mark.asyncio
async def test_check_git_repo_push_failure(
    git_repo: tuple[pathlib.Path, str], mocker: MockerFixture
):
    from src.submit import _check_git_repo

    repo, _ = git_repo

    # Create conflicting state
    other_clone = repo.parent / "other_clone"
    other_clone.mkdir()
    git_command(repo.parent, "clone", str(repo), "other_clone")

    # Create conflicting commit in other clone
    (other_clone / "conflict.txt").write_text("conflict")
    git_command(other_clone, "add", "conflict.txt")
    git_command(other_clone, "commit", "-m", "Conflicting commit")
    git_command(other_clone, "push")

    # Create local commit
    (repo / "local.txt").write_text("local")
    git_command(repo, "add", "local.txt")
    git_command(repo, "commit", "-m", "Local commit")

    echo_mock = mocker.patch("click.echo")

    mocker.patch("click.confirm", return_value=True, autospec=True)
    await _check_git_repo(repo)

    echo_mock.assert_any_call("Failed to push to git remote:")


@pytest.mark.asyncio
async def test_check_git_repo_user_abort(
    git_repo_with_remote: tuple[pathlib.Path, str], mocker
):
    from src.submit import _check_git_repo

    repo, _ = git_repo_with_remote

    # Create uncommitted change
    (repo / "new.txt").write_text("new content")
    git_command(repo, "add", "new.txt")

    mocker.patch("click.echo")
    mocker.patch("click.confirm", side_effect=click.exceptions.Abort)

    with pytest.raises(click.exceptions.Abort):
        await _check_git_repo(repo)


@pytest.fixture(name="mocked_calls")
def fixture_mocked_calls(
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
    git_repo_with_remote: tuple[pathlib.Path, str],
):
    import src.clock as clock

    repo, _ = git_repo_with_remote

    # Mock required paths and user confirmation
    mocker.patch("src.submit.AGENT_HOME_DIR", repo.parent)
    mocker.patch("src.submit._SUBMISSION_PATH", tmp_path / "submission.txt")
    mocker.patch("click.confirm", return_value=True)

    mocked_sleep = mocker.patch("asyncio.sleep", return_value=None)
    cleanup_mock = mocker.patch("src.submit.async_cleanup")
    mock_hooks = mocker.patch("src.submit.HOOKS")
    mock_hooks.submit = mocker.AsyncMock()

    # Mock clock status
    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus.RUNNING)
    mocker.patch("src.clock.clock", return_value=clock.ClockStatus.RUNNING)

    return mocked_sleep, cleanup_mock, mock_hooks


@pytest.mark.parametrize("clock_status", ["STOPPED", "RUNNING"])
@pytest.mark.asyncio
async def test_main_success(
    tmp_path: pathlib.Path,
    git_repo_with_remote: tuple[pathlib.Path, str],
    mocker: MockerFixture,
    clock_status: str,
    mocked_calls: tuple[MockType, MockType, MockType],
):
    from src.submit import _main
    import src.clock as clock

    repo, _ = git_repo_with_remote

    mocked_sleep, cleanup_mock, mock_hooks = mocked_calls

    # Mock clock status
    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus(clock_status))
    mocker.patch("src.clock.clock", return_value=clock.ClockStatus.RUNNING)

    await _main("submission")

    # verify that the task was submitted
    assert (tmp_path / "submission.txt").read_text() == "submission"
    mock_hooks.submit.assert_called_once_with("submission")

    # Verify submission commit was created and pushed
    assert git_command(repo, "log", "-1", "--pretty=%B", capture_output=True) == (
        0,
        "SUBMISSION",
    )

    # Verify the commit was pushed to remote
    remote_commits = git_command(
        repo, "ls-remote", "--heads", "origin", capture_output=True
    )
    assert remote_commits[0] == 0
    status = remote_commits[1]
    assert status and "refs/heads/main" in status

    # verify that the function waited for the user to disconnect and cleaned up
    assert mocked_sleep.call_count == 1
    assert cleanup_mock.call_count == 1


@pytest.mark.asyncio
async def test_main_no_git_repo(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
    mocked_calls: tuple[MockType, MockType, MockType],
):
    from src.submit import _main

    mocked_sleep, cleanup_mock, mock_hooks = mocked_calls

    mocker.patch("src.submit.AGENT_HOME_DIR", tmp_path / "no_repo_here")

    check_git_repo_mock = mocker.patch("src.submit._check_git_repo")
    await _main("submission")
    check_git_repo_mock.assert_not_called()

    # verify that the task was submitted without git operations
    assert (tmp_path / "submission.txt").read_text() == "submission"
    mock_hooks.submit.assert_called_once_with("submission")

    # verify cleanup
    assert mocked_sleep.call_count == 1
    assert cleanup_mock.call_count == 1


@pytest.mark.asyncio
async def test_main_user_abort_confirmation(
    tmp_path: pathlib.Path,
    git_repo_with_remote: tuple[pathlib.Path, str],
    mocker: MockerFixture,
    mocked_calls: tuple[MockType, MockType, MockType],
):
    from src.submit import _main
    import src.clock as clock

    repo, _ = git_repo_with_remote

    mocked_sleep, cleanup_mock, mock_hooks = mocked_calls

    # Mock user aborting on final confirmation
    mocker.patch("click.confirm", side_effect=click.exceptions.Abort)

    # Mock clock as running
    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus.RUNNING)

    await _main("submission")

    # Verify submission was not created
    assert not (tmp_path / "submission.txt").exists()
    mocked_sleep.assert_not_called()
    cleanup_mock.assert_not_called()
    mock_hooks.submit.assert_not_called()


@pytest.mark.asyncio
async def test_main_clock_stays_stopped(
    tmp_path: pathlib.Path,
    git_repo_with_remote: tuple[pathlib.Path, str],
    mocker: MockerFixture,
    mocked_calls: tuple[MockType, MockType, MockType],
):
    from src.submit import _main
    import src.clock as clock

    repo, _ = git_repo_with_remote

    mocked_sleep, cleanup_mock, mock_hooks = mocked_calls

    # Mock clock staying stopped
    mocker.patch("src.clock.get_status", return_value=clock.ClockStatus.STOPPED)
    mocker.patch("src.clock.clock", return_value=clock.ClockStatus.STOPPED)

    await _main("submission")

    # Verify submission was not created
    assert not (tmp_path / "submission.txt").exists()
    mocked_sleep.assert_not_called()
    cleanup_mock.assert_not_called()
    mock_hooks.submit.assert_not_called()
