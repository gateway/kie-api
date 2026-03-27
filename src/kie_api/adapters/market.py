"""KIE market adapter helpers for payload construction and response normalization."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..enums import JobState, TaskMode
from ..exceptions import ProviderResponseError
from ..models import (
    CreditBalanceResult,
    NormalizedRequest,
    StatusResult,
    SubmissionResult,
    UploadResult,
)
from ..registry.models import ModelSpec


PROVIDER_STATUS_MAP = {
    "waiting": JobState.QUEUED,
    "pending": JobState.QUEUED,
    "queue": JobState.QUEUED,
    "queuing": JobState.QUEUED,
    "queued": JobState.QUEUED,
    "processing": JobState.RUNNING,
    "running": JobState.RUNNING,
    "generating": JobState.RUNNING,
    "success": JobState.SUCCEEDED,
    "succeeded": JobState.SUCCEEDED,
    "finished": JobState.SUCCEEDED,
    "failed": JobState.FAILED,
    "fail": JobState.FAILED,
    "error": JobState.FAILED,
}


def build_market_submission_payload(request: NormalizedRequest, spec: ModelSpec) -> Dict[str, Any]:
    input_payload: Dict[str, Any] = {}

    resolved_prompt = request.final_prompt_used or request.prompt
    if resolved_prompt:
        input_payload["prompt"] = resolved_prompt

    if request.task_mode in {TaskMode.TEXT_TO_IMAGE, TaskMode.IMAGE_EDIT}:
        if request.images:
            input_payload["image_input"] = [media.url or media.path for media in request.images]
    elif request.task_mode in {TaskMode.TEXT_TO_VIDEO, TaskMode.IMAGE_TO_VIDEO}:
        if request.images:
            input_payload["image_urls"] = [media.url or media.path for media in request.images]
    elif request.task_mode == TaskMode.MOTION_CONTROL:
        input_payload["input_urls"] = [media.url or media.path for media in request.images]
        input_payload["video_urls"] = [media.url or media.path for media in request.videos]

    for option_name, option_value in request.options.items():
        option_spec = spec.options.get(option_name)
        provider_field = option_spec.provider_field if option_spec and option_spec.provider_field else option_name
        input_payload[provider_field] = option_value

    payload: Dict[str, Any] = {
        "model": request.provider_model,
        "input": input_payload,
    }
    if request.callback_url:
        payload["callBackUrl"] = request.callback_url
    return payload


def normalize_market_submission_response(
    payload: Dict[str, Any],
    provider_payload: Dict[str, Any],
    *,
    http_status: Optional[int] = None,
) -> SubmissionResult:
    if payload.get("code") != 200:
        raise ProviderResponseError(
            payload.get("msg") or "KIE task submission failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    data = payload.get("data") or {}
    task_id = data.get("taskId") or data.get("task_id") or data.get("id")
    if not task_id:
        raise ProviderResponseError(
            "submission response did not include taskId",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    return SubmissionResult(
        success=True,
        task_id=task_id,
        provider_code=payload.get("code"),
        provider_message=payload.get("msg") or payload.get("message"),
        provider_payload=provider_payload,
        raw_response=payload,
    )


def normalize_market_upload_response(
    payload: Dict[str, Any], *, http_status: Optional[int] = None
) -> UploadResult:
    success = bool(payload.get("success")) or payload.get("code") == 200
    data = payload.get("data") or {}
    if not success:
        raise ProviderResponseError(
            payload.get("msg") or "KIE upload failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    result = UploadResult(
        success=True,
        provider_code=payload.get("code"),
        provider_message=payload.get("msg") or payload.get("message"),
        file_id=data.get("fileId") or data.get("id"),
        storage_id=data.get("storageId") or data.get("storageKey"),
        file_name=data.get("fileName") or data.get("originalName"),
        file_path=data.get("filePath"),
        file_url=data.get("fileUrl"),
        download_url=data.get("downloadUrl"),
        mime_type=data.get("mimeType") or data.get("contentType"),
        content_length=_coerce_int(
            data.get("size") or data.get("contentLength") or data.get("fileSize")
        ),
        expires_at=data.get("expiresAt"),
        uploaded_at=data.get("uploadedAt"),
        raw_response=payload,
    )
    if not result.file_url and not result.download_url:
        raise ProviderResponseError(
            "upload response did not include a file URL",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )
    return result


def normalize_market_status_response(
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    *,
    http_status: Optional[int] = None,
) -> StatusResult:
    if payload.get("code") not in (None, 200):
        raise ProviderResponseError(
            payload.get("msg") or "KIE status request failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    data = payload.get("data") or payload
    resolved_task_id = task_id or data.get("taskId") or data.get("task_id")
    if not resolved_task_id:
        raise ProviderResponseError(
            "status response did not include taskId",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    provider_status = (
        data.get("status")
        or data.get("state")
        or data.get("taskStatus")
        or data.get("task_state")
    )
    provider_status_text = str(provider_status).lower() if provider_status is not None else "unknown"

    return StatusResult(
        task_id=resolved_task_id,
        state=PROVIDER_STATUS_MAP.get(provider_status_text, JobState.UNKNOWN),
        provider_code=payload.get("code"),
        provider_message=payload.get("msg") or payload.get("message"),
        provider_status=provider_status_text,
        progress=_coerce_progress(data.get("progress") or data.get("percent")),
        output_urls=_collect_output_urls(data),
        error_message=(
            data.get("errorMessage")
            or data.get("error_message")
            or data.get("failMsg")
            or data.get("message")
        ),
        raw_response=payload,
    )


def normalize_market_credit_response(
    payload: Dict[str, Any],
    *,
    endpoint_path: str,
    http_status: Optional[int] = None,
) -> CreditBalanceResult:
    if payload.get("code") not in (None, 200):
        raise ProviderResponseError(
            payload.get("msg") or "KIE credit request failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    data = payload.get("data")
    if isinstance(data, dict):
        credits = _first_number(
            data.get("remainingCredits"),
            data.get("remaining_credits"),
            data.get("credits"),
            data.get("credit"),
            data.get("balance"),
            data.get("availableCredits"),
        )
        credit_unit = data.get("creditUnit") or data.get("unit")
    else:
        credits = _first_number(data)
        credit_unit = None
    notes: List[str] = []
    if credits is None:
        notes.append(
            "The credit endpoint responded, but no machine-usable remaining-credit field was found."
        )

    return CreditBalanceResult(
        success=True,
        balance_available=credits is not None,
        available_credits=credits,
        credit_unit=credit_unit,
        endpoint_path=endpoint_path,
        provider_code=payload.get("code"),
        provider_message=payload.get("msg") or payload.get("message"),
        notes=notes,
        raw_response=payload,
    )


def _collect_output_urls(data: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for key in (
        "output",
        "outputs",
        "outputUrl",
        "output_url",
        "outputUrls",
        "output_urls",
        "resultUrl",
        "result_url",
        "resultUrls",
        "result_urls",
        "imageUrls",
        "videoUrl",
    ):
        value = data.get(key)
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, list):
            urls.extend(item for item in value if isinstance(item, str))
    result_json = data.get("resultJson") or data.get("result_json")
    if isinstance(result_json, str) and result_json.strip():
        try:
            parsed = json.loads(result_json)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            urls.extend(_collect_output_urls(parsed))
        elif isinstance(parsed, list):
            urls.extend(item for item in parsed if isinstance(item, str))
    elif isinstance(result_json, dict):
        urls.extend(_collect_output_urls(result_json))
    elif isinstance(result_json, list):
        urls.extend(item for item in result_json if isinstance(item, str))
    deduped: List[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _coerce_progress(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.rstrip("%"))
        except ValueError:
            return None
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _first_number(*values: Any) -> Optional[float]:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None
