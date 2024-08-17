import sys
import time
from util import INTERNAL_SUBMISSION_PATH, call_tool
from clock import record_clock_event


def main():
    if len(sys.argv) != 2:
        print(
            "Please provide a submission (could be an empty string), e.g 'submit! <submission>'"
        )
        sys.exit(1)

    argument = sys.argv[1]

    while True:
        confirmation = input(
            f"Do you definitely want to end the task and submit '{argument}'? (y/n): "
        ).lower()
        if confirmation == "y":
            call_tool("clock/stop")
            record_clock_event("stopped")

            print(f"SUBMITTED: {argument}")
            print("CLOCK WILL BE STOPPED AUTOMATICALLY")
            print("TASK IS OVER!")
            print("From all of the METR team: thank you for your work!")
            # Using an internal path to avoid unintended submissions if humans write to `/home/agent/submission.txt` directly
            with open(
                INTERNAL_SUBMISSION_PATH, "w"
            ) as file:  # Writing this file to alert other processes to wrap up
                file.write(argument)
                
            time.sleep(5) # Time to allow other processes to wrap up
            call_tool("submit", args=[argument])

            break
        elif confirmation == "n":
            print("Submission cancelled.")
            break
        else:
            print("Please answer 'y' or 'n'.")


if __name__ == "__main__":
    main()
