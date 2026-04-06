"""Callback parsing and future verification entry points."""

from __future__ import annotations

import json
import hashlib
import hmac
import time
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..config import KieSettings
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


def verify_callback_request(
    payload: Dict[str, Any],
    headers: Mapping[str, Any],
    *,
    secret: str,
    settings: Optional[KieSettings] = None,
    max_age_seconds: Optional[int] = None,
    now: Optional[int] = None,
) -> CallbackEvent:
    resolved_settings = settings or KieSettings()
    resolved_max_age = (
        resolved_settings.callback_max_age_seconds if max_age_seconds is None else max_age_seconds
    )
    if not verify_callback_signature(
        payload,
        headers,
        secret=secret,
        max_age_seconds=resolved_max_age,
        now=now,
    ):
        raise CallbackVerificationError("Callback signature validation failed.")

    event = parse_callback_event(payload)
    if not event.task_id:
        raise CallbackVerificationError("Callback payload does not contain a usable task id.")
    if payload.get("taskId") and str(payload.get("taskId")) != event.task_id:
        raise CallbackVerificationError("Callback payload contains conflicting top-level and nested task ids.")

    for url in event.output_urls:
        if not resolved_settings.is_trusted_callback_output_url(url):
            raise CallbackVerificationError(f"Callback output URL host is not trusted: {url!r}")
    return event


def canonicalize_callback_payload(payload: Dict[str, Any]) -> str:
    """Return a deterministic compact JSON string for audit/debug use."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


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
