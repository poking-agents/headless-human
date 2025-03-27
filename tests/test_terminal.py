from __future__ import annotations

import collections.abc
import json
import pathlib
from typing import Callable, Generator, Sequence, TextIO, TypedDict, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    import src.terminal

TEST_ROOT = pathlib.Path(__file__).parent


class CastData(TypedDict):
    cast_header: collections.abc.Mapping[str, str | int | dict[str, str]]
    events: list[src.terminal.TerminalEvent]
    prompt_event_indices: list[int]


def write_cast_header(
    f: TextIO,
    cast_header: collections.abc.Mapping[str, str | int | dict[str, str]],
) -> None:
    f.write(json.dumps(cast_header) + "\n")


def write_cast_events(
    f: TextIO,
    events: list[src.terminal.TerminalEvent],
) -> None:
    for event in events:
        f.write(json.dumps(event) + "\n")


@pytest.fixture(name="cast_data")
def fixture_cast_data() -> CastData:
    cast_raw_data = (TEST_ROOT / "wordle.cast").read_text().splitlines()
    cast_header = json.loads(cast_raw_data[0])
    cast_events = [
        (float(event[0]), event[1], event[2])
        for event in (json.loads(line) for line in cast_raw_data[1:])
    ]
    prompt_event_indices = [
        i for i in json.loads((TEST_ROOT / "wordle.cast.prompt-indices").read_text())
    ]
    return CastData(
        cast_header=cast_header,
        events=cast_events,
        prompt_event_indices=prompt_event_indices,
    )


@pytest.fixture(name="log_monitor_factory")
def fixture_log_monitor(
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
) -> Generator[
    Callable[[dict[str, str | int | dict[str, str]]], src.terminal.LogMonitor],
    None,
    None,
]:
    import src.terminal

    def create_log_monitor(
        settings: dict[str, str | int | dict[str, str]] | None = None,
    ) -> src.terminal.LogMonitor:
        if settings is None:
            settings = {"agent": {"terminal_recording": "NO_TERMINAL_RECORDING"}}

        mocker.patch.object(src.terminal, "get_settings", return_value=settings)
        return src.terminal.LogMonitor(window_id=0, log_dir=tmp_path)

    yield create_log_monitor


@pytest.mark.asyncio
async def test_logs_not_sent_if_cast_is_empty(
    log_monitor_factory: Callable[
        [dict[str, str | int | dict[str, str]]], src.terminal.LogMonitor
    ],
    mocker: MockerFixture,
) -> None:
    log_monitor = log_monitor_factory(
        {"agent": {"terminal_recording": "FULL_TERMINAL_RECORDING"}},
    )
    mocked_send_text_log = mocker.patch.object(log_monitor, "_send_text_log")
    mocked_send_gif_log = mocker.patch.object(log_monitor, "_send_gif_log")

    await log_monitor.check_for_updates()

    assert not mocked_send_text_log.called
    assert not mocked_send_gif_log.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "n, sent_logs, remaining_prompt_events",
    [
        (1, False, range(1)),
        (2, False, range(2)),
        (3, False, range(3)),
        (4, False, range(4)),
        (5, False, range(5)),
        (6, True, range(5, 6)),
        (7, True, range(5, 7)),
        (8, True, range(5, 8)),
    ],
)
async def test_logs_sent_after_n_prompt_events(
    cast_data: CastData,
    log_monitor_factory: Callable[
        [dict[str, str | int | dict[str, str]]], src.terminal.LogMonitor
    ],
    n: int,
    sent_logs: bool,
    remaining_prompt_events: Sequence[int],
    mocker: MockerFixture,
) -> None:
    log_monitor = log_monitor_factory(
        {"agent": {"terminal_recording": "FULL_TERMINAL_RECORDING"}},
    )
    mocked_send_text_log = mocker.patch.object(log_monitor, "_send_text_log")
    mocked_send_gif_log = mocker.patch.object(log_monitor, "_send_gif_log")

    log_file = log_monitor.log_file
    with open(log_file, "w") as f:
        write_cast_header(f, cast_data["cast_header"])
        write_cast_events(
            f, cast_data["events"][: cast_data["prompt_event_indices"][n - 1] + 1]
        )

    await log_monitor.check_for_updates()

    assert mocked_send_text_log.called == sent_logs
    assert mocked_send_gif_log.called == sent_logs

    start, end = remaining_prompt_events[0], remaining_prompt_events[-1]
    start_idx = cast_data["prompt_event_indices"][start]
    stop_idx = cast_data["prompt_event_indices"][end]
    assert log_monitor.new_events == [
        list(e) for e in cast_data["events"][start_idx : stop_idx + 1]
    ]
