"""Credit and balance discovery helpers."""

from __future__ import annotations

from typing import List, Optional

import httpx

from ..adapters.market import normalize_market_credit_response
from ..config import KieSettings
from ..exceptions import MissingConfigurationError, ProviderResponseError, ProviderTransportError
from ..models import CreditBalanceResult
from ._transport import ManagedHttpClientMixin, request_json


class CreditsClient(ManagedHttpClientMixin):
    """Thin client for KIE account credit discovery."""

    def __init__(self, settings: KieSettings, http_client: Optional[httpx.Client] = None):
        self.settings = settings
        self._set_http_client(http_client, timeout=settings.json_timeout())

    def get_balance(self) -> CreditBalanceResult:
        self._require_api_key()

        paths = self._candidate_paths()
        errors: List[str] = []
        for path in paths:
            try:
                response, payload = request_json(
                    self.http_client,
                    "GET",
                    f"{self.settings.market_base_url}{path}",
                    endpoint_label=path,
                    error_label="KIE credit request failed",
                    headers=self.settings.auth_headers(),
                )
            except ProviderTransportError as exc:
                errors.append(f"{path}: transport failure ({exc})")
                continue
            try:
                return normalize_market_credit_response(
                    payload,
                    endpoint_path=path,
                    http_status=response.status_code,
                )
            except ProviderResponseError as exc:
                if response.status_code == 404:
                    errors.append(f"{path}: endpoint not found")
                    continue
                if exc.http_status is not None and exc.http_status >= 500:
                    errors.append(f"{path}: provider error ({exc.message})")
                    continue
                raise

        return CreditBalanceResult(
            success=False,
            balance_available=False,
            endpoint_path=paths[0] if paths else None,
            provider_message="No machine-usable KIE credit endpoint was available.",
            notes=errors or [
                "No machine-usable KIE credit endpoint was available.",
            ],
        )

    def _candidate_paths(self) -> List[str]:
        paths = [self.settings.credits_path, *self.settings.credit_fallback_paths]
        deduped: List[str] = []
        for path in paths:
            if path not in deduped:
                deduped.append(path)
        return deduped

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for credit checks")
