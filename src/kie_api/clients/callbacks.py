"""Callback parsing and future verification entry points."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..exceptions import CallbackVerificationError


TIMESTAMP_HEADER = "X-Webhook-Timestamp"
SIGNATURE_HEADER = "X-Webhook-Signature"


class CallbackEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: Optional[str] = None
    status: Optional[str] = None
    output_urls: List[str] = Field(default_factory=list)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


def parse_callback_event(payload: Dict[str, Any]) -> CallbackEvent:
    data = payload.get("data") or payload
    urls = (
        data.get("outputs")
        or data.get("output_urls")
        or data.get("resultUrl")
        or data.get("resultUrls")
        or []
    )
    if isinstance(urls, str):
        urls = [urls]
    return CallbackEvent(
        task_id=data.get("taskId") or data.get("task_id") or payload.get("taskId"),
        status=data.get("status") or data.get("taskStatus") or data.get("state"),
        output_urls=[url for url in urls if isinstance(url, str)],
        raw_payload=payload,
    )


def build_callback_signature(task_id: str, timestamp: str, secret: str) -> str:
    message = f"{task_id}.{timestamp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_callback_signature(
    payload: Dict[str, Any],
    headers: Mapping[str, Any],
    *,
    secret: str,
    max_age_seconds: Optional[int] = None,
    now: Optional[int] = None,
) -> bool:
    task_id = _extract_task_id(payload)
    timestamp = _extract_header(headers, TIMESTAMP_HEADER)
    signature = _extract_header(headers, SIGNATURE_HEADER)

    if not secret:
        raise CallbackVerificationError("A webhook secret is required for callback verification.")
    if not task_id:
        raise CallbackVerificationError("Callback payload does not contain taskId/task_id.")
    if not timestamp:
        raise CallbackVerificationError(f"Missing {TIMESTAMP_HEADER} header.")
    if not signature:
        raise CallbackVerificationError(f"Missing {SIGNATURE_HEADER} header.")

    if max_age_seconds is not None:
        timestamp_int = _coerce_timestamp(timestamp)
        current_time = int(time.time()) if now is None else int(now)
        if abs(current_time - timestamp_int) > max_age_seconds:
            return False

    expected = build_callback_signature(task_id=task_id, timestamp=timestamp, secret=secret)
    return hmac.compare_digest(expected, str(signature))


def _extract_task_id(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data") or payload
    task_id = data.get("taskId") or data.get("task_id") or payload.get("taskId")
    return str(task_id) if task_id is not None else None


def _extract_header(headers: Mapping[str, Any], name: str) -> Optional[str]:
    lowered_name = name.lower()
    for key, value in headers.items():
        if str(key).lower() == lowered_name and value is not None:
            return str(value)
    return None


def _coerce_timestamp(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CallbackVerificationError(
            f"{TIMESTAMP_HEADER} must be an integer Unix timestamp."
        ) from exc
