"""Pricing registry backed by versioned snapshot resource files."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .. import _gpt_image_2_6 as gpt26
from ..models import EstimatedCost, NormalizedRequest
from ..registry.loader import load_latest_pricing_snapshot
from ..registry.models import PricingRule, PricingSnapshot

SEEDANCE_MODEL_KEYS = {
    "seedance-2.0",
    "seedance-2.0-fast",
    "seedance-2.0-mini",
    "seedance-2.5",
}

# KIE's square-image calculator at https://kie.ai/gpt-image-2-6 (2026-11-16).
_GPT26_SQUARE_OUTPUT_TOKENS = {
    "1k": {"low": 823, "medium": 1449, "high": 1756, "xhigh": 3122, "max": 7024},
    "2k": {"low": 1667, "medium": 2944, "high": 3568, "xhigh": 6343, "max": 14272},
    "4k": {"low": 2768, "medium": 4894, "high": 5930, "xhigh": 10542, "max": 23719},
}


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
        options = dict(request.options)
        options.update(_derive_request_pricing_options(request))
        estimate = self._estimate(request.model_key, options)
        if request.model_key in gpt26.MODEL_KEYS and estimate.billing_unit == "million_tokens":
            rule = self._rules[request.model_key]
            return _estimate_gpt26_static_image(request, estimate, rule)
        return estimate

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

        if rule.billing_unit == "million_tokens":
            # A unit rate alone cannot estimate the billable usage of a request.
            return EstimatedCost(
                model_key=model_key,
                currency=self.snapshot.currency,
                pricing_version=self.snapshot.version,
                pricing_source_kind=self.snapshot.source_kind,
                pricing_status=rule.pricing_status,
                billing_unit=rule.billing_unit,
                assumptions=list(self.snapshot.notes),
                notes=list(rule.notes),
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
                multiplier = _second_billing_duration_multiplier(
                    rule,
                    option_name,
                    options.get(option_name),
                )
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


def _estimate_gpt26_static_image(
    request: NormalizedRequest, estimate: EstimatedCost, rule: PricingRule,
) -> EstimatedCost:
    options = request.options
    if options.get("output_format", "png") not in ("png", "jpeg", "webp"):
        return estimate
    if options.get("aspect_ratio", "auto") not in ("auto", "1:1"):
        return estimate
    resolution = _normalize_option_value(options.get("resolution", "1K"))
    quality = _normalize_option_value(options.get("quality", "medium"))
    output_tokens = _GPT26_SQUARE_OUTPUT_TOKENS.get(resolution, {}).get(quality)
    output_rate = rule.token_rates.get("image_output")
    if output_tokens is None or output_rate is None:
        return estimate

    reference_count = len(gpt26.reference_images(request))
    input_credits = 0.1 + 2.2 * reference_count
    output_million_tokens = output_tokens / 1_000_000
    return estimate.model_copy(update={
        "estimated_credits": output_million_tokens * output_rate.credits + input_credits,
        "estimated_cost_usd": output_million_tokens * output_rate.usd + input_credits * 0.005,
        "has_numeric_estimate": True,
        "assumptions": [
            *estimate.assumptions,
            "KIE's square-image output estimate (also used for Auto aspect ratio).",
            "KIE's planning allowances are 0.1 credits for the prompt and 2.2 per reference image.",
        ],
        "notes": ["KIE charges for actual token usage."],
    })


def _normalize_option_value(value: Any) -> str:
    if value is None:
        return "__missing__"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).lower()


def _second_billing_duration_multiplier(
    rule: PricingRule,
    option_name: str,
    option_value: Any,
) -> Optional[float]:
    if rule.billing_unit != "second" or option_name != "duration":
        return None
    if isinstance(option_value, bool) or option_value in (None, ""):
        return None
    try:
        duration = float(option_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(duration) or duration <= 0:
        return None
    return float(math.ceil(duration))


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


def _derive_request_pricing_options(request: NormalizedRequest) -> Dict[str, Any]:
    derived: Dict[str, Any] = {}

    if request.model_key in {"kling-3.0-t2v", "kling-3.0-i2v"}:
        mode = _normalize_option_value(request.options.get("mode") or "std")
        resolution = {
            "std": "720p",
            "pro": "1080p",
            "4k": "4k",
        }.get(mode, mode)
        sound = _normalize_option_value(request.options.get("sound", True))
        derived["pricing_variant"] = f"{resolution}_{sound}"

    if request.model_key in SEEDANCE_MODEL_KEYS:
        resolution = _normalize_option_value(request.options.get("resolution") or "720p")
        has_video_input = bool(request.videos)
        derived["pricing_variant"] = (
            f"{resolution}_{'with_video_input' if has_video_input else 'no_video_input'}"
        )

    if request.model_key in {"kling-2.6-motion", "kling-3.0-motion"}:
        duration = _first_video_duration_seconds(request)
        if duration is not None:
            derived["duration"] = math.ceil(duration)

    return derived


def _first_video_duration_seconds(request: NormalizedRequest) -> Optional[float]:
    for video in request.videos:
        try:
            duration = float(video.duration_seconds) if video.duration_seconds is not None else None
        except (TypeError, ValueError):
            continue
        if duration is not None and math.isfinite(duration) and duration > 0:
            return duration
    return None
