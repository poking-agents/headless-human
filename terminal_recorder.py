import sys
import subprocess
import json
from datetime import datetime

class TerminalRecorder:
    def __init__(self, output_file):
        self.output_file = output_file

    def record(self):
        while True:
            try:
                # Get user input
                user_input = input("$ ")
                
                # Prepare the record
                record = {
                    "command": user_input,
                    "timestamp_start": datetime.now().isoformat(),
                    "stdin": user_input,
                }
                
                # Execute the command
                if user_input.lower() == 'exit':
                    record["status"] = "exit"
                    self._write_jsonl(record)
                    break
                
                start_time = datetime.now()
                result = subprocess.run(user_input, shell=True, capture_output=True, text=True)
                end_time = datetime.now()
                
                # Update the record
                record.update({
                    "timestamp_end": end_time.isoformat(),
                    "duration": (end_time - start_time).total_seconds(),
                    "status_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                })
                
                # Write to JSONL file
                self._write_jsonl(record)
                
                # Print command output to terminal
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
            except Exception as e:
                error_record = {
                    "command": user_input,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                }
                self._write_jsonl(error_record)
                print(f"An error occurred: {e}", file=sys.stderr)

    def _write_jsonl(self, record):
        with open(self.output_file, 'a') as f:
            json.dump(record, f)
            f.write('\n')

if __name__ == "__main__":
    recorder = TerminalRecorder("terminal.jsonl")
    recorder.record()