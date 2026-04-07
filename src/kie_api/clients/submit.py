"""Task submission helpers for KIE model jobs."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..adapters.market import (
    build_market_submission_payload,
    normalize_market_submission_response,
)
from ..config import KieSettings
from ..exceptions import MissingConfigurationError
from ..models import NormalizedRequest, SubmissionResult
from ..registry.loader import SpecRegistry
from ..services.preparation import RequestPreparationService
from ._transport import ManagedHttpClientMixin, request_json


class SubmitClient(ManagedHttpClientMixin):
    """Thin submission client that isolates provider field mapping."""

    def __init__(
        self,
        settings: KieSettings,
        registry: SpecRegistry,
        http_client: Optional[httpx.Client] = None,
    ):
        self.settings = settings
        self.registry = registry
        self._set_http_client(http_client, timeout=settings.json_timeout())

    def build_payload(self, request: NormalizedRequest) -> Dict[str, Any]:
        RequestPreparationService(self.registry, self.settings).ensure_submit_ready(request)
        spec = self.registry.get_model(request.model_key)
        return build_market_submission_payload(request, spec)

    def submit(self, request: NormalizedRequest) -> SubmissionResult:
        self._require_api_key()
        payload = self.build_payload(request)
        response, response_payload = request_json(
            self.http_client,
            "POST",
            f"{self.settings.market_base_url}{self.settings.create_task_path}",
            endpoint_label=self.settings.create_task_path,
            error_label="KIE task submission failed",
            headers=self.settings.auth_headers(),
            json=payload,
        )
        return normalize_market_submission_response(
            response_payload,
            payload,
            http_status=response.status_code,
        )

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for task submission")
