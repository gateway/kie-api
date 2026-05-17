from collections import deque

import pytest

from kie_api import wait_for_task
from kie_api.config import KieSettings
from kie_api.enums import JobState
from kie_api.exceptions import ProviderTransportError
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


def test_wait_for_task_passes_model_key_to_status_client(monkeypatch) -> None:
    seen = {}

    class StubStatusClient:
        def __init__(self, settings, registry=None):
            self.settings = settings
            self.registry = registry

        def get_status(self, task_id: str, model_key=None) -> StatusResult:
            seen["task_id"] = task_id
            seen["model_key"] = model_key
            seen["has_registry"] = self.registry is not None
            return StatusResult(
                task_id=task_id,
                state=JobState.SUCCEEDED,
                provider_status="success",
                output_urls=["https://cdn.example.com/song.mp3"],
            )

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)

    result = wait_for_task(
        "suno_task_1",
        model_key="suno-generate-music",
        settings=KieSettings(api_key="test-key"),
        poll_interval_seconds=0.0,
        timeout_seconds=1.0,
    )

    assert result.terminal is True
    assert seen == {
        "task_id": "suno_task_1",
        "model_key": "suno-generate-music",
        "has_registry": True,
    }


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


def test_wait_for_task_retries_transient_transport_errors(monkeypatch) -> None:
    responses = deque(
        [
            ProviderTransportError("temporary status outage"),
            ProviderTransportError("temporary status outage"),
            StatusResult(
                task_id="task_4",
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
            next_response = responses.popleft()
            if isinstance(next_response, Exception):
                raise next_response
            return next_response

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)
    monkeypatch.setattr("kie_api.api.time.sleep", lambda _: None)

    result = wait_for_task(
        "task_4",
        settings=KieSettings(api_key="test-key"),
        poll_interval_seconds=0.0,
        timeout_seconds=1.0,
    )

    assert result.terminal is True
    assert result.final_status is not None
    assert result.final_status.state == JobState.SUCCEEDED
    assert len(result.history) == 1


def test_wait_for_task_raises_after_retry_budget_exhausted(monkeypatch) -> None:
    responses = deque(
        [
            ProviderTransportError("temporary status outage"),
            ProviderTransportError("temporary status outage"),
            ProviderTransportError("temporary status outage"),
            ProviderTransportError("temporary status outage"),
        ]
    )

    class StubStatusClient:
        def __init__(self, settings):
            self.settings = settings

        def get_status(self, task_id: str) -> StatusResult:
            raise responses.popleft()

    monkeypatch.setattr("kie_api.api.StatusClient", StubStatusClient)
    monkeypatch.setattr("kie_api.api.time.sleep", lambda _: None)

    with pytest.raises(ProviderTransportError, match="temporary status outage"):
        wait_for_task(
            "task_5",
            settings=KieSettings(api_key="test-key"),
            poll_interval_seconds=0.0,
            timeout_seconds=1.0,
        )
