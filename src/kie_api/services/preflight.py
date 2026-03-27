"""Dry-run preflight helpers for pricing and confirmation gating."""

from __future__ import annotations

from typing import Callable, List, Optional

from ..config import KieSettings
from ..enums import GuardDecision
from ..models import EstimatedCost, NormalizedRequest, PreflightDecision
from .pricing import PricingRegistry

RemainingCreditsFetcher = Callable[[KieSettings], Optional[float]]


class PreflightService:
    """Estimate cost and decide whether a request should proceed."""

    def __init__(
        self,
        pricing_registry: Optional[PricingRegistry] = None,
        settings: Optional[KieSettings] = None,
        remaining_credits_fetcher: Optional[RemainingCreditsFetcher] = None,
    ):
        self.pricing_registry = pricing_registry or PricingRegistry()
        self.settings = settings or KieSettings()
        self.remaining_credits_fetcher = remaining_credits_fetcher

    def estimate(self, request: NormalizedRequest):
        return self.pricing_registry.estimate_request(request)

    def evaluate(
        self,
        request: NormalizedRequest,
        remaining_credits: Optional[float] = None,
        confirmation_granted: bool = False,
    ) -> PreflightDecision:
        estimate = self.estimate(request)
        return self.evaluate_estimate(
            estimate,
            remaining_credits=remaining_credits,
            confirmation_granted=confirmation_granted,
        )

    def evaluate_estimate(
        self,
        estimate: EstimatedCost,
        remaining_credits: Optional[float] = None,
        confirmation_granted: bool = False,
        extra_warnings: Optional[List[str]] = None,
    ) -> PreflightDecision:
        warnings = list(estimate.notes)
        if extra_warnings:
            warnings.extend(extra_warnings)
        if estimate.has_numeric_estimate and not estimate.is_authoritative:
            warnings.append(
                "Estimated cost is based on non-authoritative pricing data and should be treated as a planning aid."
            )
        checked_remaining_credits = False

        if remaining_credits is None and self.settings.api_key and self.remaining_credits_fetcher:
            remaining_credits = self.remaining_credits_fetcher(self.settings)
            checked_remaining_credits = remaining_credits is not None

        if not estimate.has_numeric_estimate:
            return PreflightDecision(
                decision=GuardDecision.WARN,
                estimated_cost=estimate,
                remaining_credits=remaining_credits,
                remaining_credits_checked=checked_remaining_credits,
                can_submit=True,
                reason="Pricing is unknown for this request.",
                warnings=warnings,
            )

        if (
            remaining_credits is not None
            and estimate.estimated_credits is not None
            and estimate.estimated_credits > remaining_credits
        ):
            return PreflightDecision(
                decision=GuardDecision.REJECT,
                estimated_cost=estimate,
                remaining_credits=remaining_credits,
                remaining_credits_checked=True,
                can_submit=False,
                reason="Estimated credits exceed remaining credits.",
                warnings=warnings,
            )

        if _exceeds_confirmation_threshold(estimate, self.settings):
            return PreflightDecision(
                decision=(
                    GuardDecision.ALLOW
                    if confirmation_granted
                    else GuardDecision.REQUIRE_CONFIRMATION
                ),
                estimated_cost=estimate,
                remaining_credits=remaining_credits,
                remaining_credits_checked=checked_remaining_credits,
                requires_confirmation=not confirmation_granted,
                can_submit=confirmation_granted,
                reason=(
                    "Explicit confirmation required for an expensive run."
                    if not confirmation_granted
                    else "Confirmation was granted for an expensive run."
                ),
                warnings=warnings,
            )

        if _exceeds_warning_threshold(estimate, self.settings):
            warnings.append("Estimated cost exceeds the warning threshold.")
            return PreflightDecision(
                decision=GuardDecision.WARN,
                estimated_cost=estimate,
                remaining_credits=remaining_credits,
                remaining_credits_checked=checked_remaining_credits,
                can_submit=True,
                reason="Estimated cost exceeds the warning threshold.",
                warnings=warnings,
            )

        return PreflightDecision(
            decision=GuardDecision.ALLOW,
            estimated_cost=estimate,
            remaining_credits=remaining_credits,
            remaining_credits_checked=checked_remaining_credits,
            can_submit=True,
            reason="Estimated cost is within the configured thresholds.",
            warnings=warnings,
        )


def _exceeds_warning_threshold(estimate, settings: KieSettings) -> bool:
    return bool(
        (
            settings.warn_credit_threshold is not None
            and estimate.estimated_credits is not None
            and estimate.estimated_credits >= settings.warn_credit_threshold
        )
        or (
            settings.warn_cost_usd_threshold is not None
            and estimate.estimated_cost_usd is not None
            and estimate.estimated_cost_usd >= settings.warn_cost_usd_threshold
        )
    )


def _exceeds_confirmation_threshold(estimate, settings: KieSettings) -> bool:
    return bool(
        (
            settings.confirm_credit_threshold is not None
            and estimate.estimated_credits is not None
            and estimate.estimated_credits >= settings.confirm_credit_threshold
        )
        or (
            settings.confirm_cost_usd_threshold is not None
            and estimate.estimated_cost_usd is not None
            and estimate.estimated_cost_usd >= settings.confirm_cost_usd_threshold
        )
    )
