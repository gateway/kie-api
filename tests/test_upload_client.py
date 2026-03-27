import pytest

from kie_api.config import KieSettings
from kie_api.exceptions import ProviderResponseError
from kie_api.clients.upload import UploadClient


def test_upload_client_normalizes_successful_response() -> None:
    client = UploadClient(KieSettings(api_key="test-key"))

    result = client.normalize_upload_response(
        {
            "success": True,
            "code": 200,
            "msg": "File upload successful",
            "data": {
                "fileId": "file_123",
                "fileName": "clip.png",
                "fileUrl": "https://files.example.com/clip.png",
                "downloadUrl": "https://files.example.com/download/file_123",
                "mimeType": "image/png",
                "expiresAt": "2026-03-28T10:30:00Z",
            },
        }
    )

    assert result.file_id == "file_123"
    assert result.download_url.endswith("file_123")


def test_upload_client_normalizes_observed_live_stream_response() -> None:
    client = UploadClient(KieSettings(api_key="test-key"))

    result = client.normalize_upload_response(
        {
            "success": True,
            "code": 200,
            "msg": "File uploaded successfully",
            "data": {
                "success": True,
                "fileName": "2way-person1.jpg",
                "filePath": "kieai/183531/images/user-uploads/2way-person1.jpg",
                "downloadUrl": "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/2way-person1.jpg",
                "fileSize": 2352983,
                "mimeType": "image/jpeg",
                "uploadedAt": "2026-03-26T07:08:46.134Z",
            },
        }
    )

    assert result.file_name == "2way-person1.jpg"
    assert result.file_path == "kieai/183531/images/user-uploads/2way-person1.jpg"
    assert result.download_url.startswith("https://tempfile.redpandaai.co/")
    assert result.content_length == 2352983
    assert result.uploaded_at == "2026-03-26T07:08:46.134Z"


def test_upload_client_raises_clear_error_on_failure() -> None:
    client = UploadClient(KieSettings(api_key="test-key"))

    with pytest.raises(ProviderResponseError, match="denied") as exc_info:
        client.normalize_upload_response({"success": False, "code": 422, "msg": "denied"})

    assert exc_info.value.provider_code == 422
