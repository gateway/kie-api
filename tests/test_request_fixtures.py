from kie_api import REQUEST_FIXTURES, build_submission_payload, normalize_request, validate_request
from kie_api.config import KieSettings
from kie_api.enums import GuardDecision, ValidationState
from kie_api.registry.models import PricingRule
from kie_api.registry.loader import load_registry
from kie_api.services.credit_guard import CreditGuard
from kie_api.services.pricing import PricingRegistry


def test_request_fixtures_validate_to_expected_states() -> None:
    registry = load_registry()

    for fixture in REQUEST_FIXTURES.values():
        normalized = normalize_request(fixture.request, registry)
        result = validate_request(normalized, registry)

        assert normalized.model_key == fixture.expected_model_key
        assert result.state == fixture.expected_state


def test_submission_ready_fixtures_build_payloads() -> None:
    registry = load_registry()
    ready_states = {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }

    for fixture in REQUEST_FIXTURES.values():
        result = validate_request(fixture.request, registry)
        if result.state not in ready_states:
            continue
        if fixture.request.images or fixture.request.videos or fixture.request.audios:
            continue

        payload = build_submission_payload(result, registry)

        assert "model" in payload
        assert "input" in payload


def test_high_cost_fixture_can_exercise_credit_guard_confirmation() -> None:
    fixture = REQUEST_FIXTURES["kling_3_pro_audio_15s"]
    pricing = PricingRegistry.from_rules(
        [PricingRule(model_key=fixture.expected_model_key, pricing_status="manual", base_credits=25)],
        version="manual",
    )
    guard = CreditGuard(pricing, KieSettings(warn_credit_threshold=10))

    result = guard.evaluate(fixture.expected_model_key, remaining_credits=100)

    assert result.decision == GuardDecision.REQUIRE_CONFIRMATION
    assert any("request-specific pricing adjustments" in warning for warning in result.warnings)
