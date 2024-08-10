import sys
from util import INTERNAL_SUBMISSION_PATH, is_clock_running
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
            if is_clock_running():
                record_clock_event("stopped")
            # Using an internal path to avoid unintended submissions if humans write to `/home/agent/submission.txt` directly
            with open(INTERNAL_SUBMISSION_PATH, "w") as file:
                file.write(argument)
            print(f"SUBMITTED: {argument}")
            print("CLOCK WILL BE STOPPED AUTOMATICALLY")
            print("TASK IS OVER!")
            print("From all of the METR team: thank you for your work!")
            break
        elif confirmation == "n":
            print("Submission cancelled.")
            break
        else:
            print("Please answer 'y' or 'n'.")


if __name__ == "__main__":
    main()
