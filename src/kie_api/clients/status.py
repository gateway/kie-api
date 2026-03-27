"""Task status helpers for KIE jobs."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..adapters.market import normalize_market_status_response
from ..config import KieSettings
from ..exceptions import MissingConfigurationError
from ..models import StatusResult


class StatusClient:
    """Thin status client that normalizes provider state variants."""

    def __init__(self, settings: KieSettings, http_client: Optional[httpx.Client] = None):
        self.settings = settings
        self.http_client = http_client or httpx.Client(timeout=settings.json_timeout())

    def get_status(self, task_id: str) -> StatusResult:
        self._require_api_key()
        response = self.http_client.get(
            f"{self.settings.market_base_url}{self.settings.status_path}",
            headers=self.settings.auth_headers(),
            params={"taskId": task_id},
        )
        return self.normalize_status_response(
            response.json(),
            task_id=task_id,
            http_status=response.status_code,
        )

    def normalize_status_response(
        self,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        http_status: Optional[int] = None,
    ) -> StatusResult:
        return normalize_market_status_response(payload, task_id=task_id, http_status=http_status)

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for status checks")
