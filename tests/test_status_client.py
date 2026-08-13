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


def test_status_client_extracts_seedance_25_frames_and_result_object() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {
            "code": 200,
            "data": {
                "taskId": "task_seedance_25",
                "state": "success",
                "resultJson": (
                    '{"resultUrls":["https://cdn.example.com/out.mp4"],'
                    '"firstFrameUrl":["https://cdn.example.com/first.jpg"],'
                    '"lastFrameUrl":["https://cdn.example.com/last.jpg"],'
                    '"resultObject":{"videoUrl":"https://cdn.example.com/alternate.mov"}}'
                ),
            },
        }
    )

    assert result.output_urls == [
        "https://cdn.example.com/out.mp4",
        "https://cdn.example.com/first.jpg",
        "https://cdn.example.com/last.jpg",
        "https://cdn.example.com/alternate.mov",
    ]


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


def test_status_client_normalizes_suno_success_response() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    result = client.normalize_status_response(
        {
            "code": 200,
            "data": {
                "taskId": "suno_task_1",
                "status": "SUCCESS",
                "response": {
                    "sunoData": [
                        {
                            "audioUrl": "https://cdn.example.com/song-1.mp3",
                            "streamAudioUrl": "https://cdn.example.com/song-1-stream.mp3",
                            "imageUrl": "https://cdn.example.com/song-1.jpeg",
                            "duration": 181.5,
                            "title": "Midnight Signal",
                            "tags": "synthwave",
                            "modelName": "V5",
                        },
                        {
                            "audioUrl": "https://cdn.example.com/song-2.mp3",
                            "title": "Midnight Signal Alt",
                        },
                    ]
                },
            },
        },
        endpoint_family="suno",
    )

    assert result.state == JobState.SUCCEEDED
    assert result.output_urls == [
        "https://cdn.example.com/song-1.mp3",
        "https://cdn.example.com/song-2.mp3",
    ]
    assert result.raw_response["suno_output_metadata"][0]["image_url"] == "https://cdn.example.com/song-1.jpeg"


def test_status_client_normalizes_suno_documented_failure_statuses() -> None:
    client = StatusClient(KieSettings(api_key="test-key"))

    for provider_status in [
        "CREATE_TASK_FAILED",
        "GENERATE_AUDIO_FAILED",
        "CALLBACK_EXCEPTION",
        "SENSITIVE_WORD_ERROR",
    ]:
        result = client.normalize_status_response(
            {
                "code": 200,
                "data": {
                    "taskId": "suno_task_failed",
                    "status": provider_status,
                    "errorMessage": "provider failed",
                },
            },
            endpoint_family="suno",
        )

        assert result.state == JobState.FAILED
        assert result.error_message == "provider failed"


def test_status_client_uses_suno_record_info_path_when_model_key_is_given() -> None:
    import httpx

    from kie_api.registry.loader import load_registry

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/generate/record-info"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "taskId": "suno_task_2",
                    "status": "PENDING",
                },
            },
        )

    client = StatusClient(
        KieSettings(api_key="test-key"),
        registry=load_registry(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_status("suno_task_2", model_key="suno-generate-music")

    assert result.state == JobState.QUEUED
