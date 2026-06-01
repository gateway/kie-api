from kie_api.config import KieSettings
from kie_api.enums import GuardDecision, PromptPolicy, TaskMode
from kie_api.models import NormalizedRequest
from kie_api.registry.models import PricingRule
from kie_api.services.credit_guard import CreditGuard
from kie_api.services.preflight import PreflightService
from kie_api.services.pricing import PricingRegistry
import pytest


def test_pricing_registry_returns_snapshot_backed_estimate() -> None:
    registry = PricingRegistry()

    estimate = registry.estimate("nano-banana-pro")

    assert estimate.has_numeric_estimate is True
    assert estimate.is_known is False
    assert estimate.is_authoritative is False
    assert estimate.pricing_version == "2026-04-29-site-pricing-page"
    assert estimate.pricing_status == "observed_site_pricing"


def test_pricing_registry_uses_observed_gpt_image_2_pricing_over_local_policy_fallback() -> None:
    registry = PricingRegistry()

    estimate = registry.estimate(
        "gpt-image-2-text-to-image",
        options={"resolution": "4K"},
    )

    assert estimate.has_numeric_estimate is True
    assert estimate.is_known is False
    assert estimate.is_authoritative is False
    assert estimate.pricing_version == "2026-04-29-site-pricing-page"
    assert estimate.pricing_status == "observed_site_pricing"
    assert estimate.estimated_credits == pytest.approx(16.0)
    assert estimate.estimated_cost_usd == pytest.approx(0.08)


def test_pricing_registry_marks_suno_pricing_unknown_until_verified() -> None:
    registry = PricingRegistry()

    estimate = registry.estimate("suno-generate-music")

    assert estimate.has_numeric_estimate is False
    assert estimate.is_known is False
    assert estimate.is_authoritative is False
    assert estimate.pricing_status == "unknown"


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
    assert estimate.applied_multipliers["duration"] == pytest.approx(10.0)
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(27.0 / 14.0)
    assert estimate.estimated_credits is not None
    assert estimate.estimated_credits > 200


def test_pricing_registry_applies_kling_4k_without_extra_sound_surcharge() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="kling-3.0-t2v",
        provider_model="kling-3.0/video",
        task_mode=TaskMode.TEXT_TO_VIDEO,
        prompt="dramatic reveal",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 5, "mode": "4K", "sound": True},
    )

    estimate = registry.estimate_request(request)

    assert estimate.applied_multipliers["duration"] == pytest.approx(5.0)
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(67.0 / 14.0)
    assert estimate.estimated_credits == pytest.approx(335.0)
    assert estimate.estimated_cost_usd == pytest.approx(1.675)


def test_pricing_registry_applies_kling_30_per_second_duration_range() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="kling-3.0-i2v",
        provider_model="kling-3.0/video",
        task_mode=TaskMode.IMAGE_TO_VIDEO,
        prompt="animate the reference frame",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 7, "mode": "4K", "sound": False},
    )

    estimate = registry.estimate_request(request)

    assert estimate.applied_multipliers["duration"] == pytest.approx(7.0)
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(67.0 / 14.0)
    assert estimate.estimated_credits == pytest.approx(469.0)
    assert estimate.estimated_cost_usd == pytest.approx(2.345)


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


def test_pricing_registry_applies_seedance_request_shape_variant() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="seedance-2.0",
        provider_model="bytedance/seedance-2",
        task_mode=TaskMode.REFERENCE_TO_VIDEO,
        prompt="use these references for motion and scene pacing",
        prompt_policy=PromptPolicy.OFF,
        videos=[
            {
                "media_type": "video",
                "url": "https://example.com/ref.mp4",
                "role": "reference",
            }
        ],
        options={"duration": 8, "resolution": "720p"},
    )

    estimate = registry.estimate_request(request)

    assert estimate.applied_multipliers["duration"] == 8.0
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(25.0 / 19.0)
    assert estimate.estimated_credits == pytest.approx(200.0)
    assert estimate.estimated_cost_usd == pytest.approx(1.0)


def test_pricing_registry_applies_seedance_1080p_variant() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="seedance-2.0",
        provider_model="bytedance/seedance-2",
        task_mode=TaskMode.TEXT_TO_VIDEO,
        prompt="cinematic city establishing shot",
        prompt_policy=PromptPolicy.OFF,
        options={"duration": 4, "resolution": "1080p"},
    )

    estimate = registry.estimate_request(request)

    assert estimate.applied_multipliers["duration"] == 4.0
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(102.0 / 19.0)
    assert estimate.estimated_credits == pytest.approx(408.0)


def test_pricing_registry_applies_seedance_fast_variant() -> None:
    registry = PricingRegistry()
    request = NormalizedRequest(
        model_key="seedance-2.0-fast",
        provider_model="bytedance/seedance-2-fast",
        task_mode=TaskMode.REFERENCE_TO_VIDEO,
        prompt="use the reference clip for motion timing",
        prompt_policy=PromptPolicy.OFF,
        videos=[
            {
                "media_type": "video",
                "url": "https://example.com/ref.mp4",
                "role": "reference",
            }
        ],
        options={"duration": 10, "resolution": "720p"},
    )

    estimate = registry.estimate_request(request)

    assert estimate.applied_multipliers["duration"] == 10.0
    assert estimate.applied_multipliers["pricing_variant"] == pytest.approx(20.0 / 15.5)
    assert estimate.estimated_credits == pytest.approx(200.0)
