import pytest

from kie_api.clients.callbacks import (
    build_callback_signature,
    canonicalize_callback_payload,
    parse_callback_event,
    verify_callback_request,
    verify_callback_signature,
)
from kie_api.config import KieSettings
from kie_api.exceptions import CallbackVerificationError


def test_parse_callback_event_normalizes_common_fields() -> None:
    event = parse_callback_event(
        {
            "data": {
                "taskId": "task_123",
                "status": "success",
                "outputs": ["https://cdn.example.com/out.mp4"],
            }
        }
    )

    assert event.task_id == "task_123"
    assert event.status == "success"
    assert event.output_urls == ["https://cdn.example.com/out.mp4"]


def test_verify_callback_signature_matches_documented_hmac_pattern() -> None:
    payload = {"data": {"taskId": "task_123"}}
    headers = {
        "X-Webhook-Timestamp": "1711111111",
        "X-Webhook-Signature": build_callback_signature(
            task_id="task_123",
            timestamp="1711111111",
            secret="top-secret",
        ),
    }

    assert verify_callback_signature(payload, headers, secret="top-secret") is True


def test_verify_callback_signature_can_fail_stale_callbacks() -> None:
    payload = {"data": {"taskId": "task_123"}}
    headers = {
        "X-Webhook-Timestamp": "1711111111",
        "X-Webhook-Signature": build_callback_signature(
            task_id="task_123",
            timestamp="1711111111",
            secret="top-secret",
        ),
    }

    assert (
        verify_callback_signature(
            payload,
            headers,
            secret="top-secret",
            max_age_seconds=60,
            now=1711111212,
        )
        is False
    )


def test_verify_callback_signature_raises_on_missing_task_id() -> None:
    with pytest.raises(CallbackVerificationError, match="taskId"):
        verify_callback_signature(
            payload={"data": {}},
            headers={
                "X-Webhook-Timestamp": "1711111111",
                "X-Webhook-Signature": "abc",
            },
            secret="top-secret",
        )


def test_verify_callback_request_requires_trusted_output_urls() -> None:
    payload = {
        "data": {
            "taskId": "task_123",
            "status": "success",
            "outputs": ["https://evil.example.com/out.mp4"],
        }
    }
    headers = {
        "X-Webhook-Timestamp": "1711111111",
        "X-Webhook-Signature": build_callback_signature(
            task_id="task_123",
            timestamp="1711111111",
            secret="top-secret",
        ),
    }

    with pytest.raises(CallbackVerificationError, match="not trusted"):
        verify_callback_request(
            payload,
            headers,
            secret="top-secret",
            settings=KieSettings(callback_trusted_output_hosts=["tempfile.aiquickdraw.com"]),
            max_age_seconds=600,
            now=1711111111,
        )


def test_verify_callback_request_rejects_conflicting_task_ids() -> None:
    payload = {"taskId": "outer_123", "data": {"taskId": "task_123"}}
    headers = {
        "X-Webhook-Timestamp": "1711111111",
        "X-Webhook-Signature": build_callback_signature(
            task_id="task_123",
            timestamp="1711111111",
            secret="top-secret",
        ),
    }

    with pytest.raises(CallbackVerificationError, match="conflicting"):
        verify_callback_request(
            payload,
            headers,
            secret="top-secret",
            settings=KieSettings(),
            max_age_seconds=600,
            now=1711111111,
        )


def test_canonicalize_callback_payload_is_deterministic() -> None:
    payload = {"b": 2, "a": {"y": 2, "x": 1}}
    assert canonicalize_callback_payload(payload) == '{"a":{"x":1,"y":2},"b":2}'
