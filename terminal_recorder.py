import sys
import subprocess
from datetime import datetime

class TerminalRecorder:
    def __init__(self, output_file):
        self.output_file = output_file

    def record(self):
        with open(self.output_file, 'a') as f:
            f.write(f"--- Recording started at {datetime.now()} ---\n")

        while True:
            try:
                # Get user input
                user_input = input("$ ")
                
                # Write user input to file
                with open(self.output_file, 'a') as f:
                    f.write(f"$ {user_input}\n")
                
                # Execute the command
                if user_input.lower() == 'exit':
                    break
                
                result = subprocess.run(user_input, shell=True, capture_output=True, text=True)
                
                # Write command output to file
                with open(self.output_file, 'a') as f:
                    f.write(result.stdout)
                    f.write(result.stderr)
                
                # Print command output to terminal
                print(result.stdout)
                print(result.stderr, file=sys.stderr)

            except Exception as e:
                print(f"An error occurred: {e}", file=sys.stderr)
                with open(self.output_file, 'a') as f:
                    f.write(f"An error occurred: {e}\n")

        with open(self.output_file, 'a') as f:
            f.write(f"--- Recording ended at {datetime.now()} ---\n")

if __name__ == "__main__":
    recorder = TerminalRecorder("terminal_record.txt")
    recorder.record()