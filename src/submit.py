from __future__ import annotations

import asyncio
import pathlib
import subprocess

import aiofiles
import click

import src.clock as clock
import src.settings as settings
from src.settings import AGENT_HOME_DIR, HOOKS, async_cleanup

_SUBMISSION_PATH = AGENT_HOME_DIR / "submission.txt"


async def _git_push(repo_dir: pathlib.Path) -> tuple[int, str]:
    """
    Returns (return_code, stdout_and_stderr)
    """
    process = subprocess.Popen(
        ["git", "push"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout, _ = process.communicate()
    output = stdout.decode().strip()
    return_code = process.returncode
    return return_code, output


async def _check_git_repo(repo_dir: pathlib.Path):
    process = subprocess.Popen(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout, _ = process.communicate()
    output = stdout.decode().strip()
    if not output:
        click.echo(f"No uncommitted changes in {repo_dir}")
    else:
        click.echo(f"Uncommitted changes in {repo_dir}:")
        click.echo(output)
        click.confirm("Are you sure you want to continue?", abort=True)
        
    settings_info = settings.get_settings()
    has_internet_access = bool(settings_info.permissions)
    
    if has_internet_access:
        return await _verify_git_repo_pushed(repo_dir)
    
    click.confirm(
        "Since this task is running on a container with no internet access, "
        "please copy the repo to your local machine (on your local machine, run `git clone ssh://baseline/home/agent baseline && cd baseline`), and then push the code from your local machine to github (let us know if you don't have the url). Let us know if you need help"
        "\n\nONLY CONFIRM ONCE THIS IS DONE.",
        abort=True
    )

async def _verify_git_repo_pushed(repo_dir: pathlib.Path):

    return_code, output = await _git_push(repo_dir)
    if return_code == 0:
        click.echo("Successfully pushed to git remote.")
        return

    click.echo("Failed to push to git remote:")
    click.echo(output)
    click.confirm("Are you sure you want to continue?", abort=True)


async def _main(submission: str):
    try:
        if (await clock.get_status()) == clock.ClockStatus.STOPPED:
            click.echo("Cannot submit: clock is stopped.")
            clock_status = await clock.clock()
            if clock_status == clock.ClockStatus.STOPPED:
                return

        solution_dir = AGENT_HOME_DIR / "solution"
        if (solution_dir / ".git").exists():
            await _check_git_repo(solution_dir)

        click.confirm(
            f"Do you definitely want to end the task and submit '{submission}'?",
            abort=True,
        )
    except click.exceptions.Abort:
        click.echo("Submission cancelled.")
        return

    click.echo(f"SUBMITTED: {submission}")
    click.echo("From all of the METR team: thank you for your work!")
    click.echo("Your task is being scored. Please do not make any changes.")

    _SUBMISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(_SUBMISSION_PATH, "w") as f:
        await asyncio.gather(
            f.write(submission),
            HOOKS.submit(submission),
        )

    click.echo("Scoring complete! You can exit the task environment now.")
    await asyncio.sleep(60)

    click.echo("Oh, you're still here?")
    click.echo("Please, exit the task environment now.")

    await async_cleanup()


@click.command(name="msubmit")
@click.argument("SUBMISSION", type=str)
def main(submission: str):
    """Submit SUBMISSION as your final solution and end the task. For most tasks,
    SUBMISSION can be an empty string, e.g. msubmit ''
    """
    asyncio.run(_main(submission))


if __name__ == "__main__":
    main()
