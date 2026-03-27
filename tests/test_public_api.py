from kie_api import (
    REQUEST_FIXTURES,
    apply_enhanced_prompt,
    ArtifactDerivativeSettings,
    ArtifactSource,
    RunArtifactCreateRequest,
    RunSourceContext,
    append_run_index,
    build_submission_payload,
    create_run_artifact,
    dry_run_prompt_enhancement,
    estimate_request_cost,
    generate_image_derivatives,
    generate_video_derivatives,
    get_latest_assets,
    get_latest_successful_run,
    get_run_by_id,
    get_run_summary,
    get_request_fixture,
    list_recent_runs,
    list_runs_by_model,
    list_runs_by_status,
    list_runs_by_tag,
    load_run_artifact,
    normalize_request,
    prepare_request_for_submission,
    rebuild_run_index,
    resolve_prompt_context,
    run_preflight,
    update_run_notes,
    validate_request,
)
from kie_api.config import KieSettings
from kie_api.enums import GuardDecision, ValidationState
from kie_api.models import RawUserRequest, UploadResult
from kie_api.registry.loader import load_registry
from typing import Optional


def test_public_api_helpers_support_wrapper_friendly_flow() -> None:
    registry = load_registry()
    fixture = get_request_fixture("nano_banana_pro_cinematic_edit")
    
    class DummyUploadClient:
        def upload_file_stream(self, file_path: str, file_name: Optional[str] = None) -> UploadResult:
            raise AssertionError("stream upload should not be used in this test")

        def upload_from_url(self, source_url: str, file_name: Optional[str] = None) -> UploadResult:
            resolved_name = file_name or "portrait.png"
            return UploadResult(
                success=True,
                file_name=resolved_name,
                file_path=f"kieai/183531/images/user-uploads/{resolved_name}",
                download_url=f"https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/{resolved_name}",
                raw_response={"success": True},
            )

    normalized = normalize_request(fixture.request, registry)
    result = validate_request(normalized, registry)
    prepared = prepare_request_for_submission(
        result,
        registry=registry,
        settings=KieSettings(api_key="test-key"),
        upload_client=DummyUploadClient(),
    )
    payload = build_submission_payload(prepared, registry, settings=KieSettings(api_key="test-key"))

    assert result.state == ValidationState.READY
    assert payload["model"] == "nano-banana-pro"
    assert payload["input"]["image_input"] == [
        "https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/portrait.png"
    ]


def test_public_api_exports_request_fixtures() -> None:
    assert "kling_3_motion_missing_video" in REQUEST_FIXTURES


def test_public_api_exports_artifact_helpers() -> None:
    assert ArtifactDerivativeSettings is not None
    assert ArtifactSource is not None
    assert RunArtifactCreateRequest is not None
    assert RunSourceContext is not None
    assert create_run_artifact is not None
    assert generate_image_derivatives is not None
    assert generate_video_derivatives is not None
    assert append_run_index is not None
    assert list_recent_runs is not None
    assert list_runs_by_model is not None
    assert list_runs_by_status is not None
    assert list_runs_by_tag is not None
    assert get_run_by_id is not None
    assert get_run_summary is not None
    assert load_run_artifact is not None
    assert get_latest_successful_run is not None
    assert get_latest_assets is not None
    assert rebuild_run_index is not None
    assert update_run_notes is not None


def test_public_api_supports_dry_run_prompt_and_preflight_helpers() -> None:
    fixture = get_request_fixture("kling_3_pro_audio_15s")

    enhancement = dry_run_prompt_enhancement(fixture.request)
    estimate = estimate_request_cost(fixture.request)
    preflight = run_preflight(
        fixture.request,
        settings=KieSettings(confirm_credit_threshold=25, warn_credit_threshold=10),
    )

    assert enhancement.profile_key == "kling_3_0_t2v_v1"
    assert estimate.pricing_version == "2026-03-26-site-pricing-page"
    assert preflight.decision == GuardDecision.REQUIRE_CONFIRMATION


def test_public_api_supports_prompt_resolution_and_final_prompt_application() -> None:
    fixture = get_request_fixture("nano_banana_pro_cinematic_edit")

    normalized = normalize_request(fixture.request)
    context = resolve_prompt_context(normalized)
    updated = apply_enhanced_prompt(
        normalized,
        "cleaned final prompt for submission",
        enhanced_prompt="cleaned final prompt for submission",
    )

    assert context.resolved_preset_key == "nano_banana_pro_image_edit_v1"
    assert str(context.input_pattern) == "image_edit"
    assert "final image-edit prompt for Nano Banana Pro" in (context.rendered_system_prompt or "")
    assert updated.final_prompt_used == "cleaned final prompt for submission"
    assert updated.enhanced_prompt == "cleaned final prompt for submission"


def test_public_api_accepts_prompt_preset_key_alias() -> None:
    normalized = normalize_request(
        RawUserRequest.model_validate(
            {
                "model_key": "kling-3.0-i2v",
                "prompt": "animate this starting frame",
                "images": ["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/start.png"],
                "options": {"duration": 5, "mode": "std"},
                "prompt_preset_key": "kling_3_0_i2v_first_frame_v1",
            }
        )
    )
    context = resolve_prompt_context(normalized)

    assert context.requested_preset_key == "kling_3_0_i2v_first_frame_v1"
    assert context.resolved_preset_key == "kling_3_0_i2v_first_frame_v1"
