"""KIE Suno adapter helpers for payload and status normalization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..enums import JobState
from ..exceptions import ProviderResponseError
from ..models import NormalizedRequest, StatusResult, SubmissionResult
from ..registry.models import ModelSpec


SUNO_STATUS_MAP = {
    "pending": JobState.QUEUED,
    "submitted": JobState.QUEUED,
    "processing": JobState.RUNNING,
    "running": JobState.RUNNING,
    "text_success": JobState.RUNNING,
    "first_success": JobState.RUNNING,
    "success": JobState.SUCCEEDED,
    "complete": JobState.SUCCEEDED,
    "completed": JobState.SUCCEEDED,
    "create_task_failed": JobState.FAILED,
    "generate_audio_failed": JobState.FAILED,
    "callback_exception": JobState.FAILED,
    "sensitive_word_error": JobState.FAILED,
    "failed": JobState.FAILED,
    "fail": JobState.FAILED,
    "error": JobState.FAILED,
}

SUNO_NON_CUSTOM_PROVIDER_FIELDS = {
    "customMode",
    "instrumental",
    "model",
}


def build_suno_submission_payload(request: NormalizedRequest, spec: ModelSpec) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    resolved_prompt = request.final_prompt_used or request.prompt
    if resolved_prompt:
        payload["prompt"] = resolved_prompt

    for option_name, option_value in request.options.items():
        option_spec = spec.options.get(option_name)
        provider_field = option_spec.provider_field if option_spec and option_spec.provider_field else option_name
        if option_value is not None:
            payload[provider_field] = option_value

    if request.callback_url:
        payload["callBackUrl"] = request.callback_url
    if payload.get("customMode") is False:
        payload = {
            key: value
            for key, value in payload.items()
            if key in SUNO_NON_CUSTOM_PROVIDER_FIELDS or key in {"prompt", "callBackUrl"}
        }
    return payload


def normalize_suno_submission_response(
    payload: Dict[str, Any],
    provider_payload: Dict[str, Any],
    *,
    http_status: Optional[int] = None,
) -> SubmissionResult:
    if payload.get("code") not in (None, 200):
        raise ProviderResponseError(
            payload.get("msg") or "KIE Suno task submission failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    data = payload.get("data") or {}
    task_id = data.get("taskId") or data.get("task_id") or data.get("id")
    if not task_id:
        raise ProviderResponseError(
            "Suno submission response did not include taskId",
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


def normalize_suno_status_response(
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    *,
    http_status: Optional[int] = None,
) -> StatusResult:
    if payload.get("code") not in (None, 200):
        raise ProviderResponseError(
            payload.get("msg") or "KIE Suno status request failed",
            provider_code=payload.get("code"),
            http_status=http_status,
            raw_response=payload,
        )

    data = payload.get("data") or payload
    resolved_task_id = task_id or data.get("taskId") or data.get("task_id")
    if not resolved_task_id:
        raise ProviderResponseError(
            "Suno status response did not include taskId",
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
    output_urls, metadata = _collect_suno_outputs(data)

    return StatusResult(
        task_id=resolved_task_id,
        state=SUNO_STATUS_MAP.get(provider_status_text, JobState.UNKNOWN),
        provider_code=payload.get("code"),
        provider_message=payload.get("msg") or payload.get("message"),
        provider_status=provider_status_text,
        progress=_coerce_progress(data.get("progress") or data.get("percent")),
        output_urls=output_urls,
        error_message=(
            data.get("errorMessage")
            or data.get("error_message")
            or data.get("failMsg")
            or data.get("message")
        ),
        raw_response={**payload, "suno_output_metadata": metadata},
    )


def _collect_suno_outputs(data: Dict[str, Any]) -> tuple[List[str], List[Dict[str, Any]]]:
    response = data.get("response") if isinstance(data.get("response"), dict) else {}
    suno_data = data.get("sunoData") or response.get("sunoData") or []
    urls: List[str] = []
    metadata: List[Dict[str, Any]] = []
    if not isinstance(suno_data, list):
        return urls, metadata

    for item in suno_data:
        if not isinstance(item, dict):
            continue
        audio_url = item.get("audioUrl")
        if isinstance(audio_url, str):
            urls.append(audio_url)
        metadata.append(
            {
                "audio_url": audio_url,
                "stream_audio_url": item.get("streamAudioUrl"),
                "image_url": item.get("imageUrl"),
                "duration": item.get("duration"),
                "title": item.get("title"),
                "tags": item.get("tags"),
                "model_name": item.get("modelName"),
            }
        )
    return _dedupe(urls), metadata


def _dedupe(values: List[str]) -> List[str]:
    result: List[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


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
