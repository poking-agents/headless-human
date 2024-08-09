# Headless-Human (alpha)


This is a prototype agent that I hope we can use for human baselines in the future.

Here's an example of it in action: https://mp4-server.koi-moth.ts.net/run/#122485/e=4646250000508648,uq

# Trying it out

To try a task inside this agent do the following:

- Clone this repo
- Start a run on this agent 
  - (e.g by running `mp4 run fermi_estimate/1_internet -o -y` inside the repo)
- Run `mp4 ssh <Run ID> --user agent` or `mp4 code <Run Id> --user agent`
- Run `bash /home/agent/.agent_code/setup.sh`

# Agent Functionality

- `note!` to take notes
- `clock!` to start and stop the serial timer
- `submit!` to submit an answer to the task
- Automatically records the terminal in which the setup script was run.   
  - (Doesn't currently record any new terminals that are opened)

# Known Issues

- Terminal gifs are currently only available for internet tasks
  - This is because MP4 agent builds do not currently support non python dependencies
  - When MP4 adds non python dependencies to the agent builds, this will be fixed
  - (This will also speed up the setup.sh script a lot for internet tasks)
- Human `clock!` commands are not currently connected to MP4's serial time counter
  - Once the next version of pyhooks is released, this will be fixed
- Doesn't currently record any new terminals that are opened after the setup script is run
  - I think this could be fixed by adding the setup script to the bashrc, but my guess is this may be a bit fiddly - so leaving it for now
