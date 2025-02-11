from __future__ import annotations

import asyncio
import pathlib
import textwrap

import click

import src.clock as clock
import src.settings as settings


async def run_command(command: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    process = await asyncio.subprocess.create_subprocess_exec(
        *command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    return_code = await process.wait()
    return return_code, stdout.decode().strip()


async def _git_push(repo_dir: pathlib.Path) -> tuple[int, str]:
    return await run_command(["git", "push"], repo_dir)


async def _create_submission_commit(repo_dir: pathlib.Path):
    commands = [
        ["git", "stash", "push"],
        ["git", "commit", "--allow-empty", "-m", "SUBMISSION"],
        ["git", "stash", "pop"],
    ]
    for command in commands:
        await run_command(command, repo_dir)


async def _get_jumphost(repo_dir: pathlib.Path) -> str:
    _, jumphost = await run_command(["ssh", "-G", "metr-baseline"], cwd=repo_dir)
    for line in jumphost.splitlines():
        if not line.lower().startswith("proxyjump "):
            continue

        proxy_jump = line.split(None, 1)[1].strip().replace("[", "").replace("]", "")
        if "@" not in proxy_jump:
            return f"ssh-user@{proxy_jump}"
        return proxy_jump
    return ""


async def git_clone_instructions(repo_dir: pathlib.Path):
    _, ip_address = await run_command(["hostname", "-I"], cwd=repo_dir)
    get_origin_failed, origin_url = await run_command(
        ["git", "remote", "get-url", "origin"], cwd=repo_dir
    )
    origin_var = ""
    origin_desc = ""
    if get_origin_failed or "No such remote" in origin_url:
        origin_url = "$ORIGIN_URL"
        origin_var = (
            "ORIGIN_URL=git@github.com:evals-sandbox/baseline-TASK-YYYY-MM-DD-NAME.git"
        )
        origin_desc = (
            " and replace TASK-YYYY-MM-DD-NAME with whatever\n"
            "is in the name of the slack channel for this task"
        )
    origin_url = origin_url.replace("ssh://github-metr/", "git@github.com:")

    jumphost_address = await _get_jumphost(repo_dir)
    if jumphost_address:
        jumphost = f" -J {jumphost_address}"
        extra_jumphost = (
            f' -o ProxyCommand=\\"ssh -i $SSH_KEY -W %h:%p {jumphost_address}\\"'
        )
        extra_jumphost = f'If the clone command fails, try with `GIT_SSH_COMMAND="ssh{extra_jumphost} -i $SSH_KEY"\n`'
    else:
        jumphost = ""
        extra_jumphost = ""

    click.confirm(
        textwrap.dedent(
            """
            This task does not have internet access, so it can't automatically push to the
            remote github repo.

            Please copy the repo (which is in `/home/agent`) to your local machine and push
            to github from there (replace `path/to/ssh/key` with the path to the ssh key 
            you used to connect to this server{origin_desc}):
            
                SSH_KEY="path/to/ssh/key"
                {origin_var}

                GIT_SSH_COMMAND="ssh{jumphost} -i $SSH_KEY" git clone agent@{ip_address}:/home/agent baseline-solution
                git -C baseline-solution remote set-url origin {origin_url}
                GIT_SSH_COMMAND="ssh -i $SSH_KEY" git -C baseline-solution push

            Refer to the Baselining Handbook for more information.
            {extra_jumphost}
            ONLY CONFIRM ONCE THIS IS DONE.
            """
        ).format(
            origin_desc=origin_desc,
            origin_var=origin_var,
            jumphost=jumphost,
            ip_address=ip_address,
            origin_url=origin_url,
            extra_jumphost=extra_jumphost,
        ),
        abort=True,
    )


async def _check_git_repo(repo_dir: pathlib.Path):
    _, output = await run_command(["git", "status", "--porcelain"], repo_dir)
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

        print(settings.AGENT_HOME_DIR)
        if (settings.AGENT_HOME_DIR / ".git").exists():
            await _check_git_repo(settings.AGENT_HOME_DIR)
        else:
            print("No git repo")

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

    await settings.HOOKS.submit(submission)

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
