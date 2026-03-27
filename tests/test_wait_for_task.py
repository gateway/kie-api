from collections import deque

from kie_api import wait_for_task
from kie_api.config import KieSettings
from kie_api.enums import JobState
from kie_api.models import StatusResult


def test_wait_for_task_returns_terminal_success(monkeypatch) -> None:
    responses = deque(
        [
            StatusResult(task_id="task_1", state=JobState.QUEUED, provider_status="waiting"),
            StatusResult(
                task_id="task_1",
                state=JobState.SUCCEEDED,
                provider_status="success",
                output_urls=["https://tempfile.aiquickdraw.com/out.jpeg"],
            ),
        ]
    )

    class StubStatusClient:
        def __init__(self, settings):
            self.settings = settings

        def get_status(self, task_id: str) -> StatusResult:
            return responses.popleft()

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)
    monkeypatch.setattr("kie_api.api.time.sleep", lambda _: None)

    result = wait_for_task(
        "task_1",
        settings=KieSettings(api_key="test-key"),
        poll_interval_seconds=0.0,
        timeout_seconds=1.0,
    )

    assert result.terminal is True
    assert result.timed_out is False
    assert result.final_status is not None
    assert result.final_status.output_urls == ["https://tempfile.aiquickdraw.com/out.jpeg"]
    assert len(result.history) == 2


def test_wait_for_task_returns_terminal_failure(monkeypatch) -> None:
    responses = deque(
        [
            StatusResult(task_id="task_2", state=JobState.QUEUED, provider_status="waiting"),
            StatusResult(
                task_id="task_2",
                state=JobState.FAILED,
                provider_status="fail",
                error_message="provider overload",
            ),
        ]
    )

    class StubStatusClient:
        def __init__(self, settings):
            self.settings = settings

        def get_status(self, task_id: str) -> StatusResult:
            return responses.popleft()

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)
    monkeypatch.setattr("kie_api.api.time.sleep", lambda _: None)

    result = wait_for_task(
        "task_2",
        settings=KieSettings(api_key="test-key"),
        poll_interval_seconds=0.0,
        timeout_seconds=1.0,
    )

    assert result.terminal is True
    assert result.final_status is not None
    assert result.final_status.state == JobState.FAILED
    assert result.final_status.error_message == "provider overload"


def test_wait_for_task_times_out_without_terminal_state(monkeypatch) -> None:
    class StubStatusClient:
        def __init__(self, settings):
            self.settings = settings

        def get_status(self, task_id: str) -> StatusResult:
            return StatusResult(
                task_id=task_id,
                state=JobState.QUEUED,
                provider_status="waiting",
            )

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)
    monkeypatch.setattr("kie_api.api.time.sleep", lambda _: None)

    result = wait_for_task(
        "task_3",
        settings=KieSettings(api_key="test-key"),
        poll_interval_seconds=0.0,
        timeout_seconds=0.0,
    )

    assert result.terminal is False
    assert result.timed_out is True
    assert result.final_status is not None
    assert result.final_status.state == JobState.QUEUED
