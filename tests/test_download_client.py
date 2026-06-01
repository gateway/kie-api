from pathlib import Path

import httpx
import pytest

from kie_api import download_output_file
from kie_api.clients.download import DownloadClient
from kie_api.config import KieSettings
from kie_api.exceptions import DownloadPolicyError
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


def test_download_client_trusts_suno_media_host_by_default(tmp_path: Path) -> None:
    body = b"fake-cover-image-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://musicfile.kie.ai/suno-cover.jpeg")
        return httpx.Response(
            200,
            headers={"Content-Type": "image/jpeg", "Content-Length": str(len(body))},
            content=body,
        )

    client = DownloadClient(
        KieSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    destination = tmp_path / "downloads" / "suno-cover.jpeg"

    result = client.download_to_path(
        "https://musicfile.kie.ai/suno-cover.jpeg",
        str(destination),
    )

    assert destination.read_bytes() == body
    assert result.destination_path == str(destination)


def test_download_client_trusts_seedance_volcengine_tos_host_by_default(tmp_path: Path) -> None:
    body = b"fake-video-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/out.mp4")
        return httpx.Response(
            200,
            headers={"Content-Type": "video/mp4", "Content-Length": str(len(body))},
            content=body,
        )

    client = DownloadClient(
        KieSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    destination = tmp_path / "downloads" / "seedance-output.mp4"

    result = client.download_to_path(
        "https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/out.mp4",
        str(destination),
    )

    assert destination.read_bytes() == body
    assert result.destination_path == str(destination)


def test_download_client_rejects_untrusted_hosts(tmp_path: Path) -> None:
    client = DownloadClient(
        KieSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"ok"))),
    )

    with pytest.raises(DownloadPolicyError, match="not trusted"):
        client.download_to_path(
            "https://example.com/out.jpeg",
            str(tmp_path / "downloads" / "out.jpeg"),
        )


def test_download_client_rejects_oversized_content_length(tmp_path: Path) -> None:
    body = b"fake-image-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "image/jpeg", "Content-Length": "50"},
            content=body,
        )

    client = DownloadClient(
        KieSettings(download_max_bytes=10),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DownloadPolicyError, match="content length exceeds"):
        client.download_to_path(
            "https://tempfile.aiquickdraw.com/out.jpeg",
            str(tmp_path / "downloads" / "out.jpeg"),
        )


def test_download_client_deletes_partial_file_when_stream_exceeds_limit(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "image/jpeg"},
            stream=httpx.ByteStream(b"1234567890"),
        )

    client = DownloadClient(
        KieSettings(download_max_bytes=8),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    destination = tmp_path / "downloads" / "out.jpeg"

    with pytest.raises(DownloadPolicyError, match="exceeded maximum allowed size"):
        client.download_to_path(
            "https://tempfile.aiquickdraw.com/out.jpeg",
            str(destination),
        )

    assert not destination.exists()
    assert not list(destination.parent.glob(".out.jpeg*.part"))


def test_download_client_enforces_optional_output_root(tmp_path: Path) -> None:
    body = b"fake-image-bytes"
    allowed_root = tmp_path / "allowed"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    client = DownloadClient(
        KieSettings(download_output_root=str(allowed_root)),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DownloadPolicyError, match="configured root"):
        client.download_to_path(
            "https://tempfile.aiquickdraw.com/out.jpeg",
            str(tmp_path / "outside" / "out.jpeg"),
        )


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
