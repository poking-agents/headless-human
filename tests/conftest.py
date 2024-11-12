import pytest


@pytest.fixture(autouse=True)
def fixture_run_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_URL", "http://localhost:8000")
    monkeypatch.setenv("RUN_ID", "123")
    monkeypatch.setenv("AGENT_TOKEN", "456")
    monkeypatch.setenv("AGENT_BRANCH_NUMBER", "0")
    monkeypatch.setenv("TASK_ID", "task/test")
    monkeypatch.setenv("PYHOOKS_DEBUG", "0")
