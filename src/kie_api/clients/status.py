"""Task status helpers for KIE jobs."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..adapters.market import normalize_market_status_response
from ..adapters.suno import normalize_suno_status_response
from ..config import KieSettings
from ..exceptions import MissingConfigurationError
from ..models import StatusResult
from ..registry.loader import SpecRegistry
from ._transport import ManagedHttpClientMixin, request_json


class StatusClient(ManagedHttpClientMixin):
    """Thin status client that normalizes provider state variants."""

    def __init__(
        self,
        settings: KieSettings,
        registry: Optional[SpecRegistry] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.settings = settings
        self.registry = registry
        self._set_http_client(http_client, timeout=settings.json_timeout())

    def get_status(self, task_id: str, model_key: Optional[str] = None) -> StatusResult:
        self._require_api_key()
        endpoint_family, endpoint_path = self._resolve_transport(model_key)
        response, payload = request_json(
            self.http_client,
            "GET",
            f"{self.settings.market_base_url}{endpoint_path}",
            endpoint_label=endpoint_path,
            error_label="KIE status request failed",
            headers=self.settings.auth_headers(),
            params={"taskId": task_id},
        )
        return self.normalize_status_response(
            payload,
            task_id=task_id,
            http_status=response.status_code,
            endpoint_family=endpoint_family,
        )

    def normalize_status_response(
        self,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        http_status: Optional[int] = None,
        endpoint_family: str = "market",
    ) -> StatusResult:
        if endpoint_family == "suno":
            return normalize_suno_status_response(payload, task_id=task_id, http_status=http_status)
        return normalize_market_status_response(payload, task_id=task_id, http_status=http_status)

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for status checks")

    def _resolve_transport(self, model_key: Optional[str]) -> tuple[str, str]:
        if model_key and self.registry:
            spec = self.registry.get_model(model_key)
            return spec.transport.endpoint_family, spec.transport.status_path
        return "market", self.settings.status_path
