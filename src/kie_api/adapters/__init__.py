"""Provider-specific payload and response adapters."""

from .market import (
    PROVIDER_STATUS_MAP,
    build_market_submission_payload,
    normalize_market_status_response,
    normalize_market_submission_response,
    normalize_market_upload_response,
)
from .suno import (
    SUNO_STATUS_MAP,
    build_suno_submission_payload,
    normalize_suno_status_response,
    normalize_suno_submission_response,
)

__all__ = [
    "PROVIDER_STATUS_MAP",
    "SUNO_STATUS_MAP",
    "build_market_submission_payload",
    "build_suno_submission_payload",
    "normalize_market_status_response",
    "normalize_market_submission_response",
    "normalize_market_upload_response",
    "normalize_suno_status_response",
    "normalize_suno_submission_response",
]
