from pathlib import Path

import httpx

from kie_api import download_output_file
from kie_api.clients.download import DownloadClient
from kie_api.config import KieSettings
from kie_api.models import DownloadResult


def test_download_client_saves_output_to_disk(tmp_path: Path) -> None:
    body = b"fake-image-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://tempfile.aiquickdraw.com/out.jpeg")
        return httpx.Response(
            200,
            headers={"Content-Type": "image/jpeg", "Content-Length": str(len(body))},
            content=body,
        )

    client = DownloadClient(
        KieSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    destination = tmp_path / "downloads" / "out.jpeg"

    result = client.download_to_path(
        "https://tempfile.aiquickdraw.com/out.jpeg",
        str(destination),
    )

    assert destination.read_bytes() == body
    assert result.destination_path == str(destination)
    assert result.content_type == "image/jpeg"
    assert result.content_length == len(body)


def test_public_download_helper_uses_download_client(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "downloaded.jpeg"

    class StubDownloadClient:
        def __init__(self, settings):
            self.settings = settings

        def download_to_path(self, source_url: str, destination_path: str):
            Path(destination_path).write_bytes(b"ok")
            return DownloadResult(
                source_url=source_url,
                destination_path=destination_path,
                http_status=200,
            )

    monkeypatch.setattr("kie_api.api.DownloadClient", StubDownloadClient)

    result = download_output_file(
        "https://tempfile.aiquickdraw.com/out.jpeg",
        str(destination),
        settings=KieSettings(),
    )

    assert result.destination_path == str(destination)
    assert destination.read_bytes() == b"ok"
