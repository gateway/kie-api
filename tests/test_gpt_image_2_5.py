from pathlib import Path

import pytest

from kie_api import build_submission_payload, normalize_request, resolve_prompt_context, validate_request
from kie_api.models import RawUserRequest
from kie_api.registry.loader import load_latest_pricing_snapshot, load_registry, load_pricing_snapshot_file
from kie_api.services.pricing import PricingRegistry
from kie_api.services.pricing_refresh import (
    PricingCatalogCapture, PricingCatalogRow, build_supported_model_snapshot,
)


KEYS = [f"gpt-image-2-5-{flavor}-{mode}" for flavor in ("flare", "sunburst")
        for mode in ("text-to-image", "image-to-image")]
RATIOS = ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16",
          "21:9", "27:16", "16:27", "9:8", "8:9"]
ROOT = Path(__file__).resolve().parents[1]
READY = {"ready", "ready_with_defaults", "ready_with_warning"}


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def request(key, **changes):
    data = dict(model_key=key, prompt="A blue ceramic mug in soft studio lighting.",
                images=["https://tempfile.redpandaai.co/kieai/reference.png"] if key.endswith("image-to-image") else [])
    data.update(changes)
    return RawUserRequest(**data)


@pytest.mark.parametrize("key", KEYS)
def test_defaults_payload_and_preset(key, registry):
    raw = request(key, callback_url="https://example.com/callback")
    normalized = normalize_request(raw, registry)
    edit = key.endswith("image-to-image")
    assert str(normalized.task_mode) == ("image_edit" if edit else "text_to_image")
    assert normalized.options == {"aspect_ratio": "auto", "resolution": "1K"}
    assert {x.field for x in normalized.defaulted_fields} == {"aspect_ratio", "resolution"}
    assert str(validate_request(normalized, registry).state) in READY
    expected_input = dict(prompt=raw.prompt, aspect_ratio="auto", resolution="1K")
    if edit:
        expected_input["input_urls"] = ["https://tempfile.redpandaai.co/kieai/reference.png"]
    assert build_submission_payload(raw, registry) == {
        "model": key, "callBackUrl": "https://example.com/callback", "input": expected_input,
    }
    context = resolve_prompt_context(normalized, registry=registry)
    mode = "image_to_image" if edit else "text_to_image"
    assert context.resolved_preset_key == f"gpt_image_2_5_{mode}_v1"
    assert str(context.input_pattern) == ("image_edit" if edit else "prompt_only")
    assert raw.prompt in context.rendered_system_prompt
    assert "{{" not in context.rendered_system_prompt
    if edit:
        assert "Reference image count: 1" in context.rendered_system_prompt
    assert registry.get_model(key).provider_model == key


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("ratio", RATIOS)
@pytest.mark.parametrize("resolution,credits", [("1k", 6), ("2k", 10), ("4k", 16)])
def test_documented_options_normalize_validate_and_price(key, ratio, resolution, credits, registry):
    normalized = normalize_request(request(key, options={"aspect_ratio": ratio, "resolution": resolution}), registry)
    # Aliases are resolved by the existing validation stage.
    validation = validate_request(normalized, registry)
    normalized = validation.normalized_request
    assert normalized.options["resolution"] == resolution.upper()
    # API docs govern: do not inherit old GPT 2 or playground-only restrictions.
    assert str(validation.state) in READY
    assert build_submission_payload(normalized, registry)["input"]["aspect_ratio"] == ratio
    estimate = PricingRegistry().estimate_request(normalized)
    assert estimate.estimated_credits == pytest.approx(credits)
    assert estimate.estimated_cost_usd == pytest.approx(credits * 0.005)
    assert estimate.pricing_status == "observed_site_pricing"
    assert not estimate.is_authoritative


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("options", [{"aspect_ratio": "5:4"}, {"aspect_ratio": "9:21"}, {"resolution": "8K"}])
def test_rejects_undocumented_values(key, options, registry):
    assert str(validate_request(request(key, options=options), registry).state) == "invalid"


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("prompt,valid", [("", False), ("x" * 20000, True), ("x" * 20001, False)])
def test_prompt_boundaries(key, prompt, valid, registry):
    assert (str(validate_request(request(key, prompt=prompt), registry).state) in READY) == valid


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("count", [0, 1, 16, 17])
def test_image_count_boundaries(key, count, registry):
    result = validate_request(request(key, images=[f"https://example.com/{i}.png" for i in range(count)]), registry)
    valid = 1 <= count <= 16 if key.endswith("image-to-image") else count == 0
    assert (str(result.state) in READY) == valid


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("field,extension", [("videos", "mp4"), ("audios", "mp3")])
def test_rejects_unsupported_media(key, field, extension, registry):
    assert str(validate_request(request(key, **{field: [f"https://example.com/ref.{extension}"]}), registry).state) == "invalid"


def test_packaged_resources_and_inherited_pricing(registry):
    packaged = load_registry(specs_root=ROOT / "src/kie_api/resources/specs")
    source_profiles = load_registry(prompt_profiles_root=ROOT / "specs/prompt_profiles")
    for key in KEYS:
        assert registry.get_model(key) == packaged.get_model(key)
        profile_key = next(iter(registry.get_model(key).prompt.default_profile_keys_by_input_pattern.values()))
        for name in ("metadata.yaml", "prompt.md"):
            assert (ROOT / "specs/prompt_profiles" / profile_key / name).read_bytes() == (
                ROOT / "src/kie_api/resources/prompt_profiles" / profile_key / name).read_bytes()
        assert key in source_profiles.get_prompt_profile(profile_key).applies_to_models
    old = load_pricing_snapshot_file(ROOT / "src/kie_api/resources/pricing/2026-08-17_site_pricing_page.yaml")
    current = {rule.model_key: rule for rule in load_latest_pricing_snapshot().rules}
    for rule in old.rules:
        assert current[rule.model_key] == rule


def test_pricing_refresh_keeps_four_models_distinct(registry):
    rows = [PricingCatalogRow(
        model_description=f"{key}, {resolution}", interface_type="image", provider="OpenAI",
        credit_price_text=str(6 + index), usd_price_text=str((6 + index) * .005),
        anchor=f"https://kie.ai/gpt-image-2-5?model={key}",
    ) for index, key in enumerate(KEYS) for resolution in ("1k", "2k", "4k")]
    capture = PricingCatalogCapture(page_url="https://kie.ai/pricing", api_base_url="https://api.kie.ai", rows=rows)
    snapshot = build_supported_model_snapshot(capture, released_on="2026-09-09", registry=registry)
    rules = {rule.model_key: rule for rule in snapshot.rules}
    for index, key in enumerate(KEYS):
        assert rules[key].base_credits == 6 + index
        assert rules[key].source_anchor_urls == [f"https://kie.ai/gpt-image-2-5?model={key}"]
