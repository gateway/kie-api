"""Upload helpers for KIE file APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from ..adapters.market import normalize_market_upload_response
from ..config import KieSettings
from ..exceptions import MissingConfigurationError
from ..models import UploadFileRequest, UploadResult, UploadUrlRequest


class UploadClient:
    """Thin client for KIE upload endpoints."""

    def __init__(self, settings: KieSettings, http_client: Optional[httpx.Client] = None):
        self.settings = settings
        self.http_client = http_client or httpx.Client(timeout=settings.upload_timeout())

    def upload_from_url(self, source_url: str, file_name: Optional[str] = None) -> UploadResult:
        request = UploadUrlRequest(source_url=source_url, file_name=file_name)
        self._require_api_key()
        payload = {"fileUrl": request.source_url, "uploadPath": self.settings.upload_default_path}
        if request.file_name:
            payload["fileName"] = request.file_name
        response = self.http_client.post(
            f"{self.settings.upload_base_url}{self.settings.upload_url_path}",
            headers=self.settings.auth_headers(),
            json=payload,
        )
        return self.normalize_upload_response(response.json(), http_status=response.status_code)

    def upload_file_stream(self, file_path: str, file_name: Optional[str] = None) -> UploadResult:
        request = UploadFileRequest(file_path=file_path, file_name=file_name)
        self._require_api_key()
        path = Path(request.file_path)
        upload_name = request.file_name or path.name
        with path.open("rb") as handle:
            response = self.http_client.post(
                f"{self.settings.upload_base_url}{self.settings.upload_stream_path}",
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                files={"file": (upload_name, handle)},
                data={
                    "fileName": upload_name,
                    "uploadPath": self.settings.upload_default_path,
                },
            )
        return self.normalize_upload_response(response.json(), http_status=response.status_code)

    def normalize_upload_response(self, payload: dict, http_status: Optional[int] = None) -> UploadResult:
        return normalize_market_upload_response(payload, http_status=http_status)

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for upload requests")
