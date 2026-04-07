from __future__ import annotations

from typing import Callable

import httpx
import pytest

from kie_api.clients.credits import CreditsClient
from kie_api.clients.download import DownloadClient
from kie_api.clients.status import StatusClient
from kie_api.clients.submit import SubmitClient
from kie_api.clients.upload import UploadClient
from kie_api.config import KieSettings
from kie_api.exceptions import ProviderResponseError, ProviderTransportError
from kie_api.models import NormalizedRequest, RawUserRequest
from kie_api.registry.loader import SpecRegistry, load_registry
from kie_api.services.normalizer import RequestNormalizer


def _build_nano_request() -> tuple[SpecRegistry, NormalizedRequest]:
    registry = load_registry()
    normalized = RequestNormalizer(registry).normalize(
        RawUserRequest(
            model_key="nano-banana-2",
            prompt="render a product hero image",
            options={"aspect_ratio": "1:1", "resolution": "1K", "output_format": "jpg"},
        )
    )
    return registry, normalized


def test_status_client_raises_transport_error_for_network_failure() -> None:
    settings = KieSettings(api_key="test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    client = StatusClient(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ProviderTransportError, match="status request failed") as exc_info:
        client.get_status("task_123")

    assert exc_info.value.endpoint == settings.status_path


def test_status_client_raises_clear_error_for_invalid_json_response() -> None:
    settings = KieSettings(api_key="test-key")
    client = StatusClient(
        settings,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html>oops</html>"))
        ),
    )

    with pytest.raises(ProviderResponseError, match="valid JSON") as exc_info:
        client.get_status("task_123")

    assert exc_info.value.http_status == 200
    assert exc_info.value.raw_response["endpoint"] == settings.status_path


def test_submit_client_raises_clear_error_for_invalid_json_response() -> None:
    registry, normalized = _build_nano_request()
    settings = KieSettings(api_key="test-key")
    client = SubmitClient(
        settings,
        registry,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="not-json"))
        ),
    )

    with pytest.raises(ProviderResponseError, match="valid JSON") as exc_info:
        client.submit(normalized)

    assert exc_info.value.raw_response["endpoint"] == settings.create_task_path


def test_upload_client_raises_transport_error_for_network_failure() -> None:
    settings = KieSettings(api_key="test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = UploadClient(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ProviderTransportError, match="upload request failed") as exc_info:
        client.upload_from_url("https://tempfile.aiquickdraw.com/in.jpeg")

    assert exc_info.value.endpoint == settings.upload_url_path


def test_upload_client_raises_clear_error_for_invalid_json_response() -> None:
    settings = KieSettings(api_key="test-key")
    client = UploadClient(
        settings,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="not-json"))
        ),
    )

    with pytest.raises(ProviderResponseError, match="valid JSON") as exc_info:
        client.upload_from_url("https://tempfile.aiquickdraw.com/in.jpeg")

    assert exc_info.value.raw_response["endpoint"] == settings.upload_url_path


def test_credits_client_falls_back_after_transport_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/chat/credit":
            raise httpx.ReadTimeout("timed out", request=request)
        assert request.url.path == "/api/v1/user/credits"
        return httpx.Response(
            200,
            json={"code": 200, "msg": "success", "data": {"credits": "42", "unit": "credits"}},
        )

    client = CreditsClient(
        KieSettings(api_key="test-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_balance()

    assert result.success is True
    assert result.available_credits == 42.0
    assert result.endpoint_path == "/api/v1/user/credits"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: CreditsClient(KieSettings(api_key="test-key")),
        lambda: StatusClient(KieSettings(api_key="test-key")),
        lambda: UploadClient(KieSettings(api_key="test-key")),
        lambda: DownloadClient(KieSettings()),
        lambda: SubmitClient(KieSettings(api_key="test-key"), load_registry()),
    ],
)
def test_owned_client_close_closes_httpx_client(factory: Callable[[], object]) -> None:
    client = factory()

    assert client.http_client.is_closed is False
    client.close()
    assert client.http_client.is_closed is True


def test_injected_http_client_is_not_closed_by_wrapper() -> None:
    shared_client = httpx.Client()
    client = StatusClient(KieSettings(api_key="test-key"), http_client=shared_client)

    client.close()

    assert shared_client.is_closed is False
    shared_client.close()
