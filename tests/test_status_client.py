from kie_api.clients.status import StatusClient
from kie_api.config import KieSettings
from kie_api.enums import JobState


def test_status_client_normalizes_queued_response() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {"code": 200, "data": {"taskId": "task_1", "status": "waiting"}}
    )

    assert result.task_id == "task_1"
    assert result.state == JobState.QUEUED


def test_status_client_normalizes_running_response() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {"code": 200, "data": {"taskId": "task_2", "status": "generating", "progress": "42"}}
    )

    assert result.state == JobState.RUNNING
    assert result.progress == 42.0


def test_status_client_normalizes_success_response() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {
            "code": 200,
            "data": {
                "taskId": "task_3",
                "status": "success",
                "outputs": ["https://cdn.example.com/output.mp4"],
            },
        }
    )

    assert result.state == JobState.SUCCEEDED
    assert result.output_urls == ["https://cdn.example.com/output.mp4"]


def test_status_client_extracts_output_urls_from_result_json_string() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {
            "code": 200,
            "data": {
                "taskId": "task_3b",
                "state": "success",
                "resultJson": '{"resultUrls":["https://tempfile.aiquickdraw.com/out.jpeg"]}',
            },
        }
    )

    assert result.state == JobState.SUCCEEDED
    assert result.output_urls == ["https://tempfile.aiquickdraw.com/out.jpeg"]


def test_status_client_normalizes_failure_response() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {
            "code": 200,
            "data": {
                "taskId": "task_4",
                "status": "fail",
                "failMsg": "provider overload",
            },
        }
    )

    assert result.state == JobState.FAILED
    assert result.error_message == "provider overload"
