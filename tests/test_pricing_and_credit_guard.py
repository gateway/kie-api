from kie_api.config import KieSettings
from kie_api.enums import GuardDecision, PromptPolicy, TaskMode
from kie_api.models import NormalizedRequest
from kie_api.registry.models import PricingRule
from kie_api.services.credit_guard import CreditGuard
from kie_api.services.preflight import PreflightService
from kie_api.services.pricing import PricingRegistry


def test_pricing_registry_returns_snapshot_backed_estimate() -> None:
    registry = PricingRegistry()

    estimate = registry.estimate("nano-banana-pro")

    assert estimate.has_numeric_estimate is True
    assert estimate.is_known is False
    assert estimate.is_authoritative is False
    assert estimate.pricing_version == "2026-03-26-site-pricing-page"
    assert estimate.pricing_status == "observed_site_pricing"


def test_pricing_registry_applies_option_multipliers() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="kling-3.0-t2v",
        provider_model="kling-3.0/video",
        task_mode=TaskMode.TEXT_TO_VIDEO,
        prompt="dramatic reveal",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 10, "mode": "pro", "sound": True},
    )

    estimate = registry.estimate_request(request)

    assert estimate.has_numeric_estimate is True
    assert estimate.is_authoritative is False
    assert estimate.applied_multipliers == {
        "duration": 10.0,
        "mode": 1.2857142857,
        "sound": 1.4285714286,
    }
    assert estimate.estimated_credits is not None
    assert estimate.estimated_credits > 200


def test_credit_guard_rejects_when_estimated_credits_exceed_balance() -> None:
    pricing = PricingRegistry.from_rules(
        [PricingRule(model_key="kling-3.0-t2v", pricing_status="manual", base_credits=20)],
        version="manual",
    )
    guard = CreditGuard(pricing)

    result = guard.evaluate("kling-3.0-t2v", remaining_credits=5)

    assert result.decision == GuardDecision.REJECT
    assert "request-specific pricing adjustments" in result.warnings[0]


def test_credit_guard_uses_request_options_when_given_a_normalized_request() -> None:
    pricing = PricingRegistry()
    guard = CreditGuard(pricing, KieSettings(confirm_credit_threshold=25, warn_credit_threshold=10))
    request = NormalizedRequest(
        model_key="kling-3.0-t2v",
        provider_model="kling-3.0/video",
        task_mode=TaskMode.TEXT_TO_VIDEO,
        prompt="dramatic reveal",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 10, "mode": "pro", "sound": True},
    )

    result = guard.evaluate(request)

    assert result.decision == GuardDecision.REQUIRE_CONFIRMATION
    assert result.requires_confirmation is True


def test_preflight_requires_confirmation_for_expensive_run() -> None:
    request = NormalizedRequest(
        model_key="kling-3.0-t2v",
        provider_model="kling-3.0/video",
        task_mode=TaskMode.TEXT_TO_VIDEO,
        prompt="dramatic reveal",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 10, "mode": "pro", "sound": True},
    )
    service = PreflightService(
        PricingRegistry(),
        KieSettings(confirm_credit_threshold=25, warn_credit_threshold=15),
    )

    result = service.evaluate(request)

    assert result.decision == GuardDecision.REQUIRE_CONFIRMATION
    assert result.requires_confirmation is True
    assert result.can_submit is False
    assert "non-authoritative pricing data" in result.warnings[-1]


def test_preflight_can_warn_without_confirmation_threshold() -> None:
    request = NormalizedRequest(
        model_key="nano-banana-2",
        provider_model="nano-banana-2",
        task_mode=TaskMode.TEXT_TO_IMAGE,
        prompt="square ad",
        prompt_policy=PromptPolicy.OFF,
    )
    service = PreflightService(PricingRegistry(), KieSettings(warn_credit_threshold=3))

    result = service.evaluate(request)

    assert result.decision == GuardDecision.WARN
    assert result.can_submit is True
