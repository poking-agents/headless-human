import pathlib
import subprocess
from unittest import mock

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


def make_repo(repo_path: pathlib.Path) -> str | None:
    """Creates a git repo with an initial commit and returns the branch name"""
    repo_path.mkdir()
    git_command(repo_path, "init")
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
    return branch


@pytest.fixture
def git_repo(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Creates a temporary git repo with an initial commit"""
    repo_path = tmp_path / "repo"
    branch = make_repo(repo_path)
    return repo_path, branch or "master"


@pytest.fixture
def remote_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Creates a bare git repository to serve as remote"""
    remote_path = tmp_path / "remote"
    remote_path.mkdir()
    git_command(remote_path, "init", "--bare")
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
async def test_create_submission_commit_adds_empty_commit(git_repo: tuple[pathlib.Path, str]):
    from src.submit import _create_submission_commit

    repo, _branch = git_repo

    await _create_submission_commit(repo)
    commit_message = git_command(repo, "log", "-1", "--pretty=%B", capture_output=True)
    assert commit_message == (0, "SUBMISSION")


@pytest.mark.asyncio
async def test_create_submission_commit_adds_tag(git_repo: tuple[pathlib.Path, str]):
    from src.submit import _create_submission_commit

    repo, _branch = git_repo

    await _create_submission_commit(repo)

    tag_commit = git_command(repo, "rev-parse", "submission", capture_output=True)
    head_commit = git_command(repo, "rev-parse", "HEAD", capture_output=True)
    assert tag_commit == head_commit


@pytest.mark.asyncio
async def test_create_submission_commit_updates_existing_tag(git_repo: tuple[pathlib.Path, str]):
    from src.submit import _create_submission_commit

    repo, _branch = git_repo

    # Create first submission
    await _create_submission_commit(repo)
    old_tag_commit = git_command(repo, "rev-parse", "submission", capture_output=True)

    # Create second submission
    await _create_submission_commit(repo)
    new_tag_commit = git_command(repo, "rev-parse", "submission", capture_output=True)

    assert old_tag_commit != new_tag_commit


@pytest.mark.asyncio
async def test_git_push_successful(git_repo_with_remote: tuple[pathlib.Path, str]):
    from src.submit import _git_push

    repo, _branch = git_repo_with_remote

    return_code, output = await _git_push(repo)
    assert return_code == 0, output
    assert "Everything up-to-date" in output


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
    git_repo_with_remote: tuple[pathlib.Path, str], mocker
):
    from src.submit import _check_git_repo

    repo, _ = git_repo_with_remote

    echo_mock = mocker.patch("click.echo")
    with mock.patch("click.confirm", return_value=True):
        await _check_git_repo(repo)

    echo_mock.assert_any_call(f"No uncommitted changes in {repo}")
    echo_mock.assert_any_call("Successfully pushed to git remote.")

    # Make sure the submission commit was created
    assert git_command(repo, "log", "-1", "--pretty=%B", capture_output=True) == (0, "SUBMISSION")


@pytest.mark.asyncio
async def test_check_git_repo_with_changes(
    git_repo_with_remote: tuple[pathlib.Path, str], mocker
):
    from src.submit import _check_git_repo

    repo, _ = git_repo_with_remote

    # Create uncommitted change
    (repo / "new.txt").write_text("new content")
    git_command(repo, "add", "new.txt")

    echo_mock = mocker.patch("click.echo")

    with mock.patch("click.confirm", return_value=True):
        await _check_git_repo(repo)

    echo_mock.assert_any_call(f"Uncommitted changes in {repo}:")
    echo_mock.assert_any_call("Successfully pushed to git remote.")

    # Make sure the submission commit was created
    assert git_command(repo, "log", "-1", "--pretty=%B", capture_output=True) == (0, "SUBMISSION")


@pytest.mark.asyncio
async def test_check_git_repo_push_failure(git_repo: tuple[pathlib.Path, str], mocker):
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

    with mock.patch("click.confirm", return_value=True):
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
