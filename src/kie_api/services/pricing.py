"""Pricing registry backed by versioned snapshot resource files."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..models import EstimatedCost, NormalizedRequest
from ..registry.loader import load_latest_pricing_snapshot
from ..registry.models import PricingRule, PricingSnapshot


class PricingRegistry:
    """Pricing lookup and estimation using versioned snapshot files."""

    def __init__(self, snapshot: Optional[PricingSnapshot] = None):
        self.snapshot = snapshot or load_latest_pricing_snapshot()
        self._rules: Dict[str, PricingRule] = {
            rule.model_key: rule for rule in self.snapshot.rules
        }

    @classmethod
    def from_rules(
        cls,
        rules: List[PricingRule],
        version: str = "manual",
        label: str = "Manual pricing registry",
        source_kind: str = "manual",
    ) -> "PricingRegistry":
        return cls(
            PricingSnapshot(
                version=version,
                label=label,
                source_kind=source_kind,
                rules=rules,
            )
        )

    def register(self, rule: PricingRule) -> None:
        self._rules[rule.model_key] = rule
        self.snapshot.rules = list(self._rules.values())

    def get_rule(self, model_key: str) -> Optional[PricingRule]:
        return self._rules.get(model_key)

    def get_option_sensitive_fields(self, model_key: str) -> List[str]:
        rule = self.get_rule(model_key)
        if not rule:
            return []
        return list(rule.option_dependent_fields)

    def estimate(
        self,
        model_key: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> EstimatedCost:
        return self._estimate(model_key, options or {})

    def estimate_request(self, request: NormalizedRequest) -> EstimatedCost:
        return self._estimate(request.model_key, request.options)

    def _estimate(self, model_key: str, options: Dict[str, Any]) -> EstimatedCost:
        rule = self._rules.get(model_key)
        if not rule:
            return EstimatedCost(
                model_key=model_key,
                is_known=False,
                has_numeric_estimate=False,
                is_authoritative=False,
                pricing_version=self.snapshot.version,
                pricing_source_kind=self.snapshot.source_kind,
                pricing_status="unknown",
                assumptions=list(self.snapshot.notes),
                notes=["Pricing is not yet defined for this model in the active snapshot."],
            )

        estimated_credits = rule.base_credits
        estimated_cost_usd = rule.base_cost_usd
        applied_multipliers: Dict[str, float] = {}
        applied_adders_credits: Dict[str, float] = {}
        applied_adders_cost_usd: Dict[str, float] = {}

        for option_name, value_map in rule.multipliers.items():
            option_value = _normalize_option_value(options.get(option_name))
            multiplier = value_map.get(option_value)
            if multiplier is None:
                continue
            applied_multipliers[option_name] = multiplier
            if estimated_credits is not None:
                estimated_credits *= multiplier
            if estimated_cost_usd is not None:
                estimated_cost_usd *= multiplier

        for option_name, value_map in rule.adders_credits.items():
            option_value = _normalize_option_value(options.get(option_name))
            credit_adder = value_map.get(option_value)
            if credit_adder is None:
                continue
            applied_adders_credits[option_name] = credit_adder
            estimated_credits = (estimated_credits or 0.0) + credit_adder

        for option_name, value_map in rule.adders_cost_usd.items():
            option_value = _normalize_option_value(options.get(option_name))
            cost_adder = value_map.get(option_value)
            if cost_adder is None:
                continue
            applied_adders_cost_usd[option_name] = cost_adder
            estimated_cost_usd = (estimated_cost_usd or 0.0) + cost_adder
        has_numeric_estimate = estimated_credits is not None or estimated_cost_usd is not None
        is_authoritative = _is_authoritative_pricing(
            pricing_status=rule.pricing_status,
            source_kind=self.snapshot.source_kind,
        )
        return EstimatedCost(
            model_key=model_key,
            estimated_credits=estimated_credits,
            estimated_cost_usd=estimated_cost_usd,
            currency=self.snapshot.currency,
            is_known=is_authoritative,
            has_numeric_estimate=has_numeric_estimate,
            is_authoritative=is_authoritative,
            pricing_version=self.snapshot.version,
            pricing_source_kind=self.snapshot.source_kind,
            pricing_status=rule.pricing_status,
            billing_unit=rule.billing_unit,
            applied_multipliers=applied_multipliers,
            applied_adders_credits=applied_adders_credits,
            applied_adders_cost_usd=applied_adders_cost_usd,
            assumptions=list(self.snapshot.notes),
            notes=list(rule.notes),
        )


def _normalize_option_value(value: Any) -> str:
    if value is None:
        return "__missing__"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).lower()


def _is_authoritative_pricing(pricing_status: str, source_kind: str) -> bool:
    authoritative_statuses = {
        "verified_provider",
        "provider_api",
        "verified_live_billing",
    }
    authoritative_source_kinds = {
        "provider_api",
        "verified_provider",
        "live_billing",
    }
    return pricing_status in authoritative_statuses or source_kind in authoritative_source_kinds
