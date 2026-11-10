"""Task submission helpers for KIE model jobs."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional

import httpx

from .. import _gpt_image_2_6 as gpt26
from ..adapters.market import (
    build_market_submission_payload,
    normalize_market_submission_response,
)
from ..adapters.suno import (
    build_suno_submission_payload,
    normalize_suno_submission_response,
)
from ..config import KieSettings
from ..enums import TaskMode, ValidationState
from ..exceptions import DownloadPolicyError, MissingConfigurationError, RequestPreparationError
from ..models import NormalizedRequest, SubmissionResult
from ..registry.loader import SpecRegistry
from ..registry.models import ModelSpec
from ..services.preparation import RequestPreparationService
from ..services.validator import RequestValidator
from ._transport import ManagedHttpClientMixin, request_json
from .download import DownloadClient


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
        if request.model_key in gpt26.MODEL_KEYS:
            validation = RequestValidator(self.registry).validate(request)
            if validation.state in {ValidationState.INVALID, ValidationState.NEEDS_INPUT}:
                details = validation.errors + [item.message for item in validation.missing_inputs]
                raise RequestPreparationError(" ".join(details))
            assert validation.normalized_request is not None
            request = validation.normalized_request
        if spec.transport.endpoint_family == "suno":
            return build_suno_submission_payload(request, spec)
        return build_market_submission_payload(request, spec)

    def submit(self, request: NormalizedRequest) -> SubmissionResult:
        self._require_api_key()
        spec = self.registry.get_model(request.model_key)
        payload = self.build_payload(request)
        if request.model_key in gpt26.MODEL_KEYS and request.task_mode == TaskMode.IMAGE_EDIT:
            self._verify_hosted_edit_images(request, spec)
        endpoint_path = spec.transport.create_path or self.settings.create_task_path
        response, response_payload = request_json(
            self.http_client,
            "POST",
            f"{self.settings.market_base_url}{endpoint_path}",
            endpoint_label=endpoint_path,
            error_label="KIE task submission failed",
            headers=self.settings.auth_headers(),
            json=payload,
        )
        if spec.transport.endpoint_family == "suno":
            return normalize_suno_submission_response(
                response_payload,
                payload,
                http_status=response.status_code,
            )
        return normalize_market_submission_response(
            response_payload,
            payload,
            http_status=response.status_code,
        )

    def _verify_hosted_edit_images(self, request: NormalizedRequest, spec: ModelSpec) -> None:
        # Check the exact URLs we submit, including caller-created PreparedRequests.
        # Use the configured upload hosts, never the caller's original third-party URLs.
        root = Path(self.settings.download_output_root) if self.settings.download_output_root else None
        try:
            if root is not None:
                root.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(dir=root, prefix="kie-edit-") as directory:
                inspected = request.model_copy(deep=True)
                for index, item in enumerate(inspected.images):
                    limit = self.settings.download_max_bytes
                    provider_limit = gpt26.edit_image_byte_limit(spec, item.role)
                    if provider_limit is not None:
                        limit = min(limit, provider_limit)
                    settings = self.settings.model_copy(update={
                        "download_output_root": directory,
                        "download_max_bytes": limit,
                        "trusted_download_hosts": self.settings.trusted_uploaded_media_hosts,
                    })
                    path = Path(directory) / f"image-{index}"
                    try:
                        DownloadClient(settings, http_client=self.http_client).download_to_path(
                            item.url or "", str(path), anonymous=True,
                        )
                    except (DownloadPolicyError, httpx.HTTPError) as exc:
                        raise RequestPreparationError(
                            f"Could not verify images[{index}] ({item.role or 'reference'}). "
                            "Use a readable image on a trusted KIE upload host within the download size limit."
                        ) from exc
                    item.path = str(path)
                    item.url = None
                errors = gpt26.validate_edit_images(inspected, spec)
        except OSError as exc:
            raise RequestPreparationError("Could not store temporary copies for edit image verification.") from exc
        if errors:
            raise RequestPreparationError(" ".join(f"{item.field}: {item.message}" for item in errors))

    def _require_api_key(self) -> None:
        if not self.settings.api_key:
            raise MissingConfigurationError("KIE_API_KEY is required for task submission")
