# Headless-Human (alpha)


This is a prototype agent that I hope we can use for human baselines in the future.

Here's an example of it in action: https://mp4-server.koi-moth.ts.net/run/#122485/e=4646250000508648,uq

# Trying it out

To try a task inside this agent do the following:

- Clone this repo
- Start a run on this agent 
  - (e.g by running `mp4 run fermi_estimate/1_internet -o -y` inside the repo)
- Run `mp4 ssh <Run ID> --user agent` or `mp4 code <Run Id> --user agent`

# Agent Functionality

- `note!` to take notes
- `clock!` to start and stop the serial timer
- Automatically records the terminal in which the setup script was run