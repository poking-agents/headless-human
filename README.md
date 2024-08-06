# Human (alpha)


This is a prototype agent that I hope we can use for human baselines in the future.

Here's an example of it in action: https://mp4-server.koi-moth.ts.net/run/#122092/e=1596306600526119,uq

# Trying it out

To try a task inside this agent do the following:

- Clone this repo
- Start a run on this agent 
  - (e.g by running `mp4 run crossword/5x5_verify -o` inside the repo)
- Run `mp4 code <Run ID> --user agent` 

Then to try the agent-specific functionality

- `cd .agent_code`
- To take a note: `python note.py`
- To start or stop the clock: `python clock.py`



# TODOs (feel v free to PR)

- Sort out paths so scripts can be called from anywhere
- Maybe add aliases and a human start script to load these aliases?
- Remove agent token dependence. 
  - Currently am writing agent token to a text file (oop) even though I don't think we need it anymore
- More readable styling and formatting for transcript entries
  

# Misc

## How it works
_Disclaimer: I don't know what i'm doing_

- The main agent loop seems like its tied in to mp4 quite tightly. 
- Originally I tried to have the human ssh in and start their own main process but that was a bit of a mess.
- Now the agent basically just forwards environment state changes to hooks. 
- That way the agent can be essentially controlled by the human, but MP4 still gets what it expects with respect to processes existing and ports being connected in whatever way it wants.

## Terminal Recorder
There is also a really cursed terminal recorder in here atm (`.agent_code/terminal_recorder.py`). I'd recommend against trying to use it in baselines. Maybe we could make something better though.
