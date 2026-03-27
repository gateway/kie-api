"""Backward-compatible wrapper around the dry-run preflight service."""

from __future__ import annotations

from typing import Optional, Union

from ..config import KieSettings
from ..models import CreditGuardResult, NormalizedRequest
from .preflight import PreflightService
from .pricing import PricingRegistry


class CreditGuard:
    """Compatibility wrapper for request-aware and model-key-only cost checks."""

    def __init__(self, pricing_registry: PricingRegistry, settings: Optional[KieSettings] = None):
        resolved_settings = settings or KieSettings()
        if (
            resolved_settings.confirm_credit_threshold is None
            and resolved_settings.warn_credit_threshold is not None
        ):
            resolved_settings = resolved_settings.model_copy(
                update={"confirm_credit_threshold": resolved_settings.warn_credit_threshold}
            )
        self.preflight = PreflightService(pricing_registry, settings=resolved_settings)

    def evaluate(
        self,
        request_or_model_key: Union[str, NormalizedRequest],
        remaining_credits: Optional[float] = None,
        confirmation_granted: bool = False,
    ) -> CreditGuardResult:
        if isinstance(request_or_model_key, NormalizedRequest):
            result = self.preflight.evaluate(
                request_or_model_key,
                remaining_credits=remaining_credits,
                confirmation_granted=confirmation_granted,
            )
            return _to_credit_guard_result(result)

        model_key = request_or_model_key
        estimate = self.preflight.pricing_registry.estimate(model_key)
        option_sensitive_fields = self.preflight.pricing_registry.get_option_sensitive_fields(model_key)
        warnings = [
            "Model-key-only credit evaluation may omit request-specific pricing adjustments."
        ]
        if option_sensitive_fields:
            warnings.append(
                "Model-key-only credit evaluation may omit option-sensitive pricing fields: "
                + ", ".join(option_sensitive_fields)
                + "."
            )
        result = self.preflight.evaluate_estimate(
            estimate,
            remaining_credits=remaining_credits,
            confirmation_granted=confirmation_granted,
            extra_warnings=warnings,
        )
        return _to_credit_guard_result(result)


def _to_credit_guard_result(result) -> CreditGuardResult:
    return CreditGuardResult(
        decision=result.decision,
        estimated_cost=result.estimated_cost,
        remaining_credits=result.remaining_credits,
        remaining_credits_checked=result.remaining_credits_checked,
        requires_confirmation=result.requires_confirmation,
        can_submit=result.can_submit,
        reason=result.reason,
        warnings=result.warnings,
    )
