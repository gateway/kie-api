"""Helpers for downloading generated output assets."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from ..config import KieSettings
from ..models import DownloadResult


class DownloadClient:
    """Thin client for downloading output assets from result URLs."""

    def __init__(self, settings: Optional[KieSettings] = None, http_client: Optional[httpx.Client] = None):
        self.settings = settings or KieSettings()
        self.http_client = http_client or httpx.Client(timeout=self.settings.json_timeout())

    def download_to_path(self, source_url: str, destination_path: str) -> DownloadResult:
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with self.http_client.stream("GET", source_url) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)

        return DownloadResult(
            source_url=source_url,
            destination_path=str(destination),
            content_type=response.headers.get("Content-Type"),
            content_length=_coerce_int(response.headers.get("Content-Length")),
            http_status=response.status_code,
        )


def _coerce_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
