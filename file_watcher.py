import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import git
from datetime import datetime
import json
from typing import Optional, Tuple
from util import use_hook, tool_log_styles, INTERNAL_SUBMISSION_PATH

class GitAutoCommit(FileSystemEventHandler):
    def __init__(self, path: str, size_limit: int) -> None:
        self.path = Path(path)
        self.exclude_paths = ["/home/agent/.agent_code/submission.txt", "/home/agent/.auto-git/"]
        self.size_limit = size_limit
        self.export_trigger_path = Path("/home/agent/.agent_code/submission.txt")
        self.auto_repo_path = self.path / '.auto-git'
        self.commit_log_path = self.auto_repo_path / 'commit_log.jsonl'
        self.bundle_path = self.auto_repo_path / 'commit_bundle.bundle'
        self.commit_log_path.touch(exist_ok=True)
        self.setup_auto_repo()

    def setup_auto_repo(self) -> None:
        self.auto_repo_path.mkdir(parents=True, exist_ok=True)
        if not (self.auto_repo_path / '.git').exists():
            git.Repo.init(self.auto_repo_path)
            print(f"Initialized new git repository in {self.auto_repo_path}")
        self.repo = git.Repo(self.auto_repo_path)

    def on_created(self, event) -> None:
        self._handle_file_event(event, "created")

    def on_modified(self, event) -> None:
        self._handle_file_event(event, "modified")

    def on_deleted(self, event) -> None:
        if not event.is_directory:
            file_path = Path(event.src_path)
            relative_path = file_path.relative_to(self.path)
            repo_file_path = self.auto_repo_path / relative_path
            if repo_file_path.exists() and not self._is_excluded(file_path):
                self.repo.git.rm(relative_path)
                self._commit_changes(str(relative_path), "deleted")

    def on_moved(self, event) -> None:
        if not event.is_directory:
            src_path = Path(event.src_path)
            dest_path = Path(event.dest_path)
            src_relative = src_path.relative_to(self.path)
            dest_relative = dest_path.relative_to(self.path)
            if not self._is_excluded(dest_path) and dest_path.stat().st_size <= self.size_limit:
                self.repo.git.mv(str(src_relative), str(dest_relative))
                self._commit_changes(f"{src_relative} -> {dest_relative}", "moved")

    def _handle_file_event(self, event, action: str) -> None:
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self._is_excluded(file_path) and file_path.stat().st_size <= self.size_limit:
                self._add_file(file_path, action)

    def _is_excluded(self, file_path: Path) -> bool:
        return any(str(file_path).startswith(exclude_path) for exclude_path in self.exclude_paths)

    def _add_file(self, file_path: Path, action: str) -> None:
        if not self._is_excluded(file_path):
            relative_path = file_path.relative_to(self.path)
            dest_path = self.auto_repo_path / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(file_path.read_bytes())
            self.repo.git.add(str(relative_path))
            self._commit_changes(str(relative_path), action)

    def _commit_changes(self, file_path: str, action: str) -> None:
        try:
            self.repo.git.commit('-m', f'Auto-commit: {file_path} {action}')
            print(f"Committed {action} in {file_path}")
            serial_time = use_hook("get_usage")["usage"]["total_seconds"]
            self._log_commit(file_path, action, serial_time)
        except git.GitCommandError as e:
            print(f"Git error: {e}")

    def _log_commit(self, file_path: str, action: str, serial_time: float) -> None:
        log_entry = {
            'file_changed': file_path,
            'action': action,
            'commit_hash': self.repo.head.commit.hexsha,
            'commit_msg': self.repo.head.commit.message.strip(),
            'timestamp': datetime.now().isoformat(),
            'serial_time': serial_time
        }
        use_hook("log_with_attributes", args=[tool_log_styles["auto_commit"], f"💾 Commit at {use_hook('get_usage')['usage']['total_seconds']}"])
        with self.commit_log_path.open('a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def create_bundle(self, output_path: Path) -> Optional[Path]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bundle_name = f"auto_commit_bundle_{timestamp}.bundle"
            bundle_path = output_path / bundle_name
            self.repo.git.bundle('create', str(bundle_path), 'HEAD', '--all')
            print(f"Created bundle: {bundle_path}")
            return bundle_path
        except git.GitCommandError as e:
            print(f"Error creating bundle: {e}")
            return None

    def export(self, output_path: Path) -> Tuple[Path, Path]:
        bundle_path = self.create_bundle(output_path)
        return bundle_path or Path(), self.commit_log_path
    
class SubmissionEventHandler(FileSystemEventHandler):
    def __init__(self, file_watcher: GitAutoCommit) -> None:
        self.submission_path = INTERNAL_SUBMISSION_PATH
        self.file_watcher = file_watcher
        
    def on_created(self, event) -> None:
        if event.src_path == self.submission_path:
            self.file_watcher.export()
        

def run_auto_commit(repo_path: str, size_limit: int) -> GitAutoCommit:
    file_watcher = GitAutoCommit(repo_path, size_limit)
    observer = Observer()
    observer.schedule(file_watcher, repo_path, recursive=True)
    observer.start()
    
    submission_event_handler = SubmissionEventHandler(file_watcher)
    submission_observer = Observer()
    submission_observer.schedule(submission_event_handler, INTERNAL_SUBMISSION_PATH)
    submission_observer.start()
    print(f"Watching for changes in {repo_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        submission_observer.stop()
    observer.join()
    submission_observer.join()
    return file_watcher

if __name__ == "__main__":
    repo_path = Path("/home/agent")
    size_limit = 5 * 1024 * 1024  # 5 MB in bytes
    file_watcher = run_auto_commit(str(repo_path), size_limit)