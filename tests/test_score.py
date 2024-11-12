from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

import pyhooks
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="mock_log")
def fixture_mock_log(mocker: MockerFixture):
    async def stub_log(*args, **kwargs):
        if not args:
            return None

        loop = asyncio.get_running_loop()
        return loop.create_task(stub_log())

    mock_log = mocker.patch("pyhooks.Hooks.log", autospec=True, side_effect=stub_log)
    return mock_log


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("score", "expected_score_output"),
    (
        (0, "Score: 0"),
        (0.5, "Score: 0.5"),
        (1.23423423423, "Score: 1.23"),
        (float("nan"), "submission is invalid"),
    ),
)
@pytest.mark.parametrize(
    "exec_result",
    (
        None,
        {
            "stdout": "foo",
            "stderr": "bar",
            "exitStatus": 0,
        },
    ),
)
@pytest.mark.parametrize("message", (None, {"foo": "bar"}))
async def test_score(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
    score: float,
    expected_score_output: str,
    exec_result: dict[str, str] | None,
    message: dict[str, str] | None,
):
    import src.score

    expected_result = {
        "status": "invalidSubmission" if math.isnan(score) else "scoringSuccess",
        "score": score,
        "message": message,
        "execResult": exec_result,
    }

    def stub_trpc_raw_request(reqtype: str, route: str, data_arg: dict, **kwargs):
        if route == "score":
            return expected_result
        return None

    mock_trpc_raw_request = mocker.patch.object(
        pyhooks, "trpc_server_request", autospec=True, side_effect=stub_trpc_raw_request
    )

    result = await src.score.score()

    assert result == expected_result

    output = capsys.readouterr().out
    assert expected_score_output in output
    assert ("foo: bar" in output) is (message is not None)
    assert ("EXECUTION RESULTS" in output) is (exec_result is not None)
    assert mock_trpc_raw_request.call_args_list[0].args == (
        "mutation",
        "log",
        {
            "index": mocker.ANY,
            "calledAt": mocker.ANY,
            "runId": 123,
            "agentBranchNumber": 0,
            "content": {"attributes": None, "content": ("Scoring...",)},
        },
    )
