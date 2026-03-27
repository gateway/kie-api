"""Package exceptions."""

from __future__ import annotations

from typing import Any, Dict, Optional


class KieApiError(Exception):
    """Base package error."""


class SpecValidationError(KieApiError):
    """Raised when a model spec or prompt profile is malformed."""


class ModelNotFoundError(KieApiError):
    """Raised when a model key cannot be resolved."""


class RequestNormalizationError(KieApiError):
    """Raised when a raw request cannot be normalized safely."""


class RequestPreparationError(KieApiError):
    """Raised when a request is not safe to submit or cannot be prepared."""


class ArtifactProcessingError(KieApiError):
    """Raised when run artifact creation or derivative generation fails."""


class ProviderResponseError(KieApiError):
    """Raised when KIE returns an invalid or unsuccessful payload."""

    def __init__(
        self,
        message: str,
        *,
        provider_code: Optional[Any] = None,
        http_status: Optional[int] = None,
        raw_response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider_code = provider_code
        self.http_status = http_status
        self.raw_response = raw_response or {}


class MissingConfigurationError(KieApiError):
    """Raised when required runtime configuration is absent."""


class CallbackVerificationError(KieApiError):
    """Raised when webhook signature verification inputs are missing or invalid."""


class PromptTemplateRenderError(KieApiError):
    """Raised when a prompt preset template cannot be rendered safely."""
