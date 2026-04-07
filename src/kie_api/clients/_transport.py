"""Shared transport helpers for KIE provider clients."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from ..exceptions import ProviderResponseError, ProviderTransportError


class ManagedHttpClientMixin:
    """Track whether a client instance owns its underlying httpx client."""

    http_client: httpx.Client
    _owns_http_client: bool

    def _set_http_client(self, http_client: Optional[httpx.Client], *, timeout: httpx.Timeout) -> None:
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if getattr(self, "_owns_http_client", False):
            self.http_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def request_json(
    http_client: httpx.Client,
    method: str,
    url: str,
    *,
    endpoint_label: str,
    error_label: str,
    **kwargs: Any,
) -> Tuple[httpx.Response, Dict[str, Any]]:
    try:
        response = http_client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise ProviderTransportError(
            f"{error_label}: {exc}",
            endpoint=endpoint_label,
            original_error=exc,
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raw_text: Optional[str]
        try:
            raw_text = response.text[:1000]
        except Exception:
            raw_text = None
        raise ProviderResponseError(
            f"{error_label}: response was not valid JSON",
            http_status=response.status_code,
            raw_response={
                "endpoint": endpoint_label,
                "raw_text": raw_text,
            },
        ) from exc

    if not isinstance(payload, dict):
        raise ProviderResponseError(
            f"{error_label}: expected JSON object response",
            http_status=response.status_code,
            raw_response={
                "endpoint": endpoint_label,
                "payload_type": type(payload).__name__,
            },
        )

    return response, payload
