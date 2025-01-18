from __future__ import annotations
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
import pytest


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def fixture_run_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_URL", "http://localhost:8000")
    monkeypatch.setenv("RUN_ID", "123")
    monkeypatch.setenv("AGENT_TOKEN", "456")
    monkeypatch.setenv("AGENT_BRANCH_NUMBER", "0")
    monkeypatch.setenv("TASK_ID", "task/test")
    monkeypatch.setenv("PYHOOKS_DEBUG", "0")


@pytest.fixture(name="mock_hooks")
def mock_hooks(mocker: MockerFixture):
    mocker.patch("pyhooks.Hooks.log", AsyncMock())
