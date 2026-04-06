"""Helpers for downloading generated output assets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx

from ..config import KieSettings
from ..exceptions import DownloadPolicyError
from ..models import DownloadResult


class DownloadClient:
    """Thin client for downloading output assets from result URLs."""

    def __init__(self, settings: Optional[KieSettings] = None, http_client: Optional[httpx.Client] = None):
        self.settings = settings or KieSettings()
        self.http_client = http_client or httpx.Client(timeout=self.settings.json_timeout())

    def download_to_path(self, source_url: str, destination_path: str) -> DownloadResult:
        self._validate_source_url(source_url)
        destination = self._resolve_destination(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_destination = destination.with_name(f".{destination.name}.part")

        try:
            with self.http_client.stream("GET", source_url) as response:
                response.raise_for_status()
                content_length = _coerce_int(response.headers.get("Content-Length"))
                self._validate_content_length(content_length)
                bytes_written = 0
                with temp_destination.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        bytes_written += len(chunk)
                        if bytes_written > self.settings.download_max_bytes:
                            raise DownloadPolicyError(
                                f"download exceeded maximum allowed size of {self.settings.download_max_bytes} bytes"
                            )
                        handle.write(chunk)
                os.replace(temp_destination, destination)
        except Exception:
            temp_destination.unlink(missing_ok=True)
            raise

        return DownloadResult(
            source_url=source_url,
            destination_path=str(destination),
            content_type=response.headers.get("Content-Type"),
            content_length=content_length if content_length is not None else bytes_written,
            http_status=response.status_code,
        )

    def _validate_source_url(self, source_url: str) -> None:
        parsed = httpx.URL(source_url)
        if parsed.scheme != "https":
            raise DownloadPolicyError("download source URLs must use https")
        if parsed.username or parsed.password:
            raise DownloadPolicyError("download source URLs must not contain userinfo")
        if not self.settings.is_trusted_download_url(source_url):
            raise DownloadPolicyError(f"download source host is not trusted: {parsed.host!r}")

    def _resolve_destination(self, destination_path: str) -> Path:
        destination = Path(destination_path)
        if ".." in destination.parts:
            raise DownloadPolicyError("download destination must not contain parent-directory traversal")
        if destination.exists() and destination.is_dir():
            raise DownloadPolicyError("download destination must be a file path, not a directory")
        if self.settings.download_output_root:
            allowed_root = Path(self.settings.download_output_root).resolve()
            resolved_destination = destination.resolve(strict=False)
            # When a wrapper exposes downloads to users, keep writes inside a single configured root.
            if not _is_relative_to(resolved_destination, allowed_root):
                raise DownloadPolicyError(
                    f"download destination must stay within configured root {allowed_root}"
                )
            return resolved_destination
        return destination

    def _validate_content_length(self, content_length: Optional[int]) -> None:
        if content_length is not None and content_length > self.settings.download_max_bytes:
            raise DownloadPolicyError(
                f"download content length exceeds maximum allowed size of {self.settings.download_max_bytes} bytes"
            )


def _coerce_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
