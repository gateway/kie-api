"""Upload-first request preparation helpers."""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from ..config import KieSettings
from ..enums import ValidationState
from ..exceptions import RequestPreparationError
from ..models import (
    MediaReference,
    NormalizedRequest,
    PreparedRequest,
    RawUserRequest,
    UploadResult,
    ValidationResult,
)
from ..registry.loader import SpecRegistry
from ..services.normalizer import RequestNormalizer
from ..services.validator import RequestValidator
from ..clients.upload import UploadClient


ReadyRequest = Union[RawUserRequest, NormalizedRequest, ValidationResult]


class RequestPreparationService:
    """Prepare a request for submission by uploading all media first."""

    def __init__(
        self,
        registry: SpecRegistry,
        settings: KieSettings,
        upload_client: Optional[UploadClient] = None,
    ):
        self.registry = registry
        self.settings = settings
        self.upload_client = upload_client or UploadClient(settings)

    def prepare(self, request: ReadyRequest) -> PreparedRequest:
        normalized = self._resolve_ready_request(request)
        prepared_request = normalized.model_copy(deep=True)
        upload_results: List[UploadResult] = []
        reused_media: List[MediaReference] = []
        warnings: List[str] = []
        original_media = {
            "images": [media.model_dump() for media in prepared_request.images],
            "videos": [media.model_dump() for media in prepared_request.videos],
            "audios": [media.model_dump() for media in prepared_request.audios],
        }

        prepared_request.images = self._prepare_media_list(
            prepared_request.images,
            upload_results=upload_results,
            reused_media=reused_media,
        )
        prepared_request.videos = self._prepare_media_list(
            prepared_request.videos,
            upload_results=upload_results,
            reused_media=reused_media,
        )
        prepared_request.audios = self._prepare_media_list(
            prepared_request.audios,
            upload_results=upload_results,
            reused_media=reused_media,
        )

        prepared_request.debug = {
            **prepared_request.debug,
            "original_media": original_media,
            "upload_results": [result.model_dump() for result in upload_results],
            "reused_uploaded_media": [media.model_dump() for media in reused_media],
        }

        if reused_media:
            warnings.append(
                "Trusted KIE-hosted media URLs were reused without reupload."
            )

        return PreparedRequest(
            normalized_request=prepared_request,
            upload_results=upload_results,
            reused_uploaded_media=reused_media,
            warnings=warnings,
            debug={
                "original_media": original_media,
            },
        )

    def ensure_submit_ready(self, request: NormalizedRequest) -> None:
        invalid_media: List[str] = []
        for field_name, media_list in (
            ("images", request.images),
            ("videos", request.videos),
            ("audios", request.audios),
        ):
            for index, media in enumerate(media_list):
                if media.path:
                    invalid_media.append(
                        f"{field_name}[{index}] still points to local path {media.path!r}"
                    )
                    continue
                if media.url and not self.settings.is_trusted_uploaded_url(media.url):
                    invalid_media.append(
                        f"{field_name}[{index}] points to non-KIE URL host {media.url!r}"
                    )
        if invalid_media:
            raise RequestPreparationError(
                "Submission payloads must only contain KIE-uploaded media URLs. "
                + "; ".join(invalid_media)
            )

    def _prepare_media_list(
        self,
        media_list: List[MediaReference],
        *,
        upload_results: List[UploadResult],
        reused_media: List[MediaReference],
    ) -> List[MediaReference]:
        prepared: List[MediaReference] = []
        for media in media_list:
            if media.url and self.settings.is_trusted_uploaded_url(media.url):
                prepared.append(media.model_copy(deep=True))
                reused_media.append(media.model_copy(deep=True))
                continue

            if media.path:
                upload_result = self.upload_client.upload_file_stream(
                    media.path,
                    file_name=media.filename,
                )
            elif media.url:
                upload_result = self.upload_client.upload_from_url(
                    media.url,
                    file_name=media.filename,
                )
            else:  # pragma: no cover - guarded by MediaReference validation
                raise RequestPreparationError("media reference did not contain a path or URL")

            upload_results.append(upload_result)
            resolved_url = upload_result.download_url or upload_result.file_url
            if not resolved_url:
                raise RequestPreparationError(
                    "KIE upload succeeded but did not return a submit-usable URL."
                )
            prepared.append(
                MediaReference(
                    media_type=media.media_type,
                    url=resolved_url,
                    filename=upload_result.file_name or media.filename,
                    mime_type=upload_result.mime_type or media.mime_type,
                    source="uploaded",
                )
            )
        return prepared

    def _resolve_ready_request(self, request: ReadyRequest) -> NormalizedRequest:
        if isinstance(request, RawUserRequest):
            normalized = RequestNormalizer(self.registry).normalize(request)
            validation = RequestValidator(self.registry).validate(normalized)
            return _require_ready_validation(validation)
        if isinstance(request, ValidationResult):
            return _require_ready_validation(request)
        return request


def _require_ready_validation(validation: ValidationResult) -> NormalizedRequest:
    ready_states = {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }
    if validation.state not in ready_states or validation.normalized_request is None:
        raise RequestPreparationError(
            "prepare_request_for_submission requires a request in a ready state; "
            f"received {validation.state}."
        )
    return validation.normalized_request
