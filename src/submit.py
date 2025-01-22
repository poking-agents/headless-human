from __future__ import annotations

import asyncio
import pathlib
import textwrap

import aiofiles
import click

import src.clock as clock
import src.settings as settings

_SUBMISSION_PATH = settings.AGENT_HOME_DIR / "submission.txt"


async def _git_push(repo_dir: pathlib.Path) -> tuple[int, str]:
    process = await asyncio.subprocess.create_subprocess_exec(
        "git",
        "push",
        cwd=repo_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    output = stdout.decode().strip()
    return_code = await process.wait()
    return return_code, output


async def _create_submission_commit(repo_dir: pathlib.Path):
    # Stash any changes
    stash_process = await asyncio.subprocess.create_subprocess_exec(
        "git",
        "stash",
        "push",
        cwd=repo_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await stash_process.communicate()

    # Add empty commit
    commit_process = await asyncio.subprocess.create_subprocess_exec(
        "git",
        "commit",
        "--allow-empty",
        "-m",
        "SUBMISSION",
        cwd=repo_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await commit_process.communicate()

    # Pop stashed changes
    pop_process = await asyncio.subprocess.create_subprocess_exec(
        "git",
        "stash",
        "pop",
        cwd=repo_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    return await pop_process.communicate()


async def git_clone_instructions(repo_dir: pathlib.Path):
    process = await asyncio.subprocess.create_subprocess_exec(
        "hostname",
        "-I",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()

    click.confirm(
        textwrap.dedent(
            f"""
            This task does not have internet access, so it can't automatically push to the
            remote github repo.

            Please copy the repo (which is in `/home/agent`) to your local machine and push
            to github from there:

                mkdir baseline-solution
                git clone agent@{stdout.decode().strip()}:/home/agent.
                git remote set-url origin git@github.com:evals-sandbox/baseline-TASK_NAME-YYYY-MM-DD-NAME
                GIT_SSH_COMMAND='ssh -i path/to/ssh/key' git push

            Where `TASK_NAME-YYYY-MM-DD-NAME` can be copied from the slack channel for 
            this task, and `path/to/ssh/key` is the path to the ssh key you used to connect
            to this server. 

            Refer to the Baselining Handbook for more information.

            ONLY CONFIRM ONCE THIS IS DONE.
            """
        ),
        abort=True,
    )


async def _check_git_repo(repo_dir: pathlib.Path):
    process = await asyncio.subprocess.create_subprocess_exec(
        "git",
        "status",
        "--porcelain",
        cwd=repo_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    output = stdout.decode().strip()
    if not output:
        click.echo(f"No uncommitted changes in {repo_dir}")
    else:
        click.echo(f"Uncommitted changes in {repo_dir}:")
        click.echo(output)
        click.confirm("Are you sure you want to continue?", abort=True)

    await _create_submission_commit(repo_dir)

    if "full internet" not in settings.get_settings().get("task", {}).get(
        "permissions", []
    ):
        await git_clone_instructions(repo_dir)
        return

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

        if (settings.AGENT_HOME_DIR / ".git").exists():
            await _check_git_repo(settings.AGENT_HOME_DIR)

        click.confirm(
            f"Do you definitely want to end the task and submit '{submission}'? This will disconnect you from the task environment and you won't be able to reconnect.",
            abort=True,
        )
    except click.exceptions.Abort:
        click.echo("Submission cancelled.")
        return

    click.echo(f"SUBMITTED: {submission}")
    click.echo(
        f"Time taken: {await clock.get_time_elapsed()}. If you believe this is incorrect, please report it to us."
    )
    click.echo("From all of the METR team: thank you for your work!")
    click.echo("Your task is being scored. Please do not make any changes.")

    _SUBMISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(_SUBMISSION_PATH, "w") as f:
        await asyncio.gather(
            f.write(submission),
            settings.HOOKS.submit(submission),
        )

    click.echo("Scoring complete! You can exit the task environment now.")
    await asyncio.sleep(60)

    click.echo("Oh, you're still here?")
    click.echo("Please, exit the task environment now.")

    await settings.async_cleanup()


@click.command(name="msubmit")
@click.argument("SUBMISSION", type=str)
def main(submission: str):
    """Submit SUBMISSION as your final solution and end the task. For most tasks,
    SUBMISSION can be an empty string, e.g. msubmit ''
    """
    asyncio.run(_main(submission))


if __name__ == "__main__":
    main()
