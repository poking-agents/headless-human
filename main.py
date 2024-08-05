import time
from util import hooks
from pyhooks.types import MiddlemanSettings, RunUsageAndLimits
from terminal_recorder import TerminalRecorder

async def main(*args):
        
    usage = await hooks.get_usage()
    hooks.log(f"Usage: {usage}")
    task = await hooks.getTask()
    hooks.log(f"Task: {task}")
    
    while True:
        time.sleep(5)
        
if __name__ == "__main__":
    hooks.main(main)