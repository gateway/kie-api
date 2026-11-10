import json
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image

from kie_api import (
    build_submission_payload,
    normalize_request,
    prepare_request_for_submission,
    resolve_prompt_context,
    run_preflight,
    validate_request,
)
from kie_api.clients.submit import SubmitClient
from kie_api.clients.upload import UploadClient
from kie_api.config import KieSettings
from kie_api.exceptions import RequestPreparationError
from kie_api.models import PreparedRequest, RawUserRequest
from kie_api.registry.loader import load_latest_pricing_snapshot, load_registry, load_pricing_snapshot_file
from kie_api.services.pricing import PricingRegistry
from kie_api.services.pricing_refresh import (
    PricingCatalogCapture, PricingCatalogRow, build_supported_model_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
TEXT = "gpt-image-2-6-sunburst-text-to-image"
EDIT = "gpt-image-2-6-sunburst-image-to-image"
KEYS = [TEXT, EDIT, TEXT.replace("sunburst", "flare"), EDIT.replace("sunburst", "flare")]
HOST = "https://tempfile.redpandaai.co/kieai"
READY = {"ready", "ready_with_defaults", "ready_with_warning"}


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def raw(key=TEXT, **changes):
    values = {"model_key": key, "prompt": "A ceramic mug."}
    if key.endswith("image-to-image"):
        values["images"] = [f"{HOST}/ref.png"]
    values.update(changes)
    return RawUserRequest(**values)


@pytest.mark.parametrize("key", KEYS)
def test_card_defaults_preset_and_provider_payload(key, registry):
    request = raw(key, callback_url="https://example.com/callback")
    validation = validate_request(request, registry)
    assert validation.state in READY
    expected = {
        "prompt": request.prompt, "aspect_ratio": "auto", "resolution": "1K",
        "quality": "medium", "output_format": "png", "complexity": "high", "moderation": "low",
    }
    edit = key.endswith("image-to-image")
    if edit:
        expected["input_urls"] = [f"{HOST}/ref.png"]
    assert build_submission_payload(validation, registry) == {
        "model": key.replace("2-6-", "2-6/"),
        "input": expected,
        "callBackUrl": "https://example.com/callback",
    }
    profile_mode = "image_to_image" if edit else "text_to_image"
    context = resolve_prompt_context(validation.normalized_request, registry=registry)
    assert context.resolved_preset_key == f"gpt_image_2_6_{profile_mode}_v1"
    assert request.prompt in context.rendered_system_prompt


def test_source_and_packaged_cards_and_profiles_match(registry):
    package = ROOT / "src/kie_api/resources"
    source = load_registry(specs_root=ROOT / "specs", prompt_profiles_root=ROOT / "specs/prompt_profiles")
    assert {key for key in registry.model_specs if key.startswith("gpt-image-2-6-")} == set(KEYS)
    for key in KEYS:
        spec = registry.get_model(key)
        assert spec == source.get_model(key)
        profile = next(iter(spec.prompt.default_profile_keys_by_input_pattern.values()))
        for name in ("metadata.yaml", "prompt.md"):
            relative = Path("prompt_profiles") / profile / name
            assert (ROOT / "specs" / relative).read_bytes() == (package / relative).read_bytes()


@pytest.mark.parametrize(("options", "field"), [
    ({"output_compression": 25}, "output_compression"),
    ({"output_format": "jpg", "output_compression": False}, "output_compression"),
    ({"output_format": "jpeg", "output_compression": 101}, "output_compression"),
    ({"output_format": "webp", "output_compression": -1}, "output_compression"),
    ({"output_format": "jpeg", "background": "transparent"}, "background"),
    ({"output_format": "svg", "background": "transparent"}, "background"),
    ({"resolution": "2k", "background": "opaque"}, "background"),
    ({"resolution": "4K", "background": "auto"}, "background"),
    ({"frame_count": 9}, "frame_count"),
    ({"size": "512x512"}, "size"),
    ({"output_format": "gif", "frame_count": 1}, "frame_count"),
    ({"output_format": "gif", "frame_count": 17}, "frame_count"),
    ({"output_format": "gif", "frame_duration_ms": 19}, "frame_duration_ms"),
    ({"output_format": "gif", "frame_duration_ms": 2001}, "frame_duration_ms"),
    ({"output_format": "gif", "frame_duration_ms": 25}, "frame_duration_ms"),
    ({"output_format": "gif", "size": "0x512"}, "size"),
    ({"output_format": "gif", "size": "511x512"}, "size"),
    ({"output_format": "gif", "size": "1024x1024", "frame_count": 2}, "size"),
    ({"output_format": "gif", "size": "768x768", "frame_count": 13}, "size"),
    ({"output_format": "gif", "size": "16x512"}, "size"),
    ({"output_format": "gif", "size": "1024x256", "frame_count": 13}, "size"),
    ({"output_format": "gif", "size": "1280x768", "frame_count": 9}, "size"),
    ({"output_format": "gif", "size": "960x960", "frame_count": 12}, "size"),
    ({"output_format": "svg", "frame_duration_ms": 200}, "frame_duration_ms"),
    ({"output_format": "svg", "svg_model": "gpt-5.4-mini"}, "svg_model"),
    ({"svg_model": "gpt-6-sol"}, "svg_model"),
    ({"reasoning_effort": "max"}, "reasoning_effort"),
    ({"web_search": True}, "web_search"),
    ({"prompt": "overwrite the actual prompt"}, "prompt"),
    ({"svg": {"model": "gpt-6-sol"}}, "svg"),
    ({"output_format": ["gif"], "frame_count": 9}, "output_format"),
])
def test_invalid_option_and_format_combinations(options, field, registry):
    result = validate_request(raw(options=options), registry)
    assert result.state == "invalid"
    assert any(item.field == field for item in result.impossible_inputs)


@pytest.mark.parametrize(("options", "provider_options"), [
    ({"resolution": "4k", "aspect_ratio": "auto"}, {"resolution": "4K", "aspect_ratio": "auto"}),
    ({"quality": "max", "complexity": "low"}, {"quality": "max", "complexity": "low"}),
    ({"output_format": "jpg", "output_compression": 0}, {"output_format": "jpeg", "output_compression": 0}),
    ({"output_format": "webp", "output_compression": 100, "background": "transparent"},
     {"output_format": "webp", "output_compression": 100, "background": "transparent"}),
    ({"output_format": "gif", "size": "512x512", "frame_count": 16, "frame_duration_ms": 2000},
     {"output_format": "gif", "size": "512x512", "frame_count": 16, "frame_duration_ms": 2000}),
    ({"output_format": "gif", "size": "384x1152", "frame_count": 2, "frame_duration_ms": "20",
      "background": "transparent"},
     {"output_format": "gif", "size": "384x1152", "frame_count": 2, "frame_duration_ms": 20,
      "background": "transparent"}),
    ({"output_format": "gif", "size": "768x768", "frame_count": 12},
     {"output_format": "gif", "size": "768x768", "frame_count": 12}),
    ({"output_format": "svg", "svg_model": "gpt-6-sol"}, {"output_format": "svg", "svg": {"model": "gpt-6-sol"}}),
])
def test_valid_payload_boundaries(options, provider_options, registry):
    payload = build_submission_payload(raw(options=options), registry)["input"]
    assert provider_options.items() <= payload.items()
    assert "svg_model" not in payload
    assert "reasoning_effort" not in payload


def test_prompt_limit_including_rewritten_prompt(registry):
    assert validate_request(raw(prompt=" "), registry).state == "needs_input"
    assert validate_request(raw(prompt="x" * 32000), registry).state in READY
    assert validate_request(raw(prompt="x" * 32001), registry).state == "invalid"
    rewritten = normalize_request(raw(), registry).model_copy(update={"final_prompt_used": "x" * 32001})
    with pytest.raises(RequestPreparationError, match="final prompt"):
        build_submission_payload(rewritten, registry)


def test_edit_role_count_and_input_conflicts(registry):
    refs = [f"{HOST}/ref{i}.png" for i in range(17)]
    markup = {"role": "markup", "url": f"{HOST}/markup.png"}
    mask = {"role": "mask", "url": f"{HOST}/mask.png"}
    assert validate_request(raw(EDIT, images=[mask]), registry).state == "needs_input"
    payload = build_submission_payload(raw(EDIT, images=[markup, *refs[:16]]), registry)["input"]
    assert payload["input_urls"] == refs[:16]
    assert payload["markup"] == markup["url"]
    assert "mask_url" not in payload
    context = resolve_prompt_context(normalize_request(raw(EDIT, images=[markup, *refs[:16]]), registry),
                                     registry=registry)
    assert "Reference image count: 16" in context.rendered_system_prompt
    assert "Region aid: markup" in context.rendered_system_prompt
    for bad_images in ([markup, *refs], [mask, markup, refs[0]], [mask, mask, refs[0]]):
        assert validate_request(raw(EDIT, images=bad_images), registry).state == "invalid"
    for format_name in ("gif", "svg"):
        assert validate_request(
            raw(EDIT, images=[refs[0], mask], options={"output_format": format_name}), registry
        ).state == "invalid"
        assert validate_request(
            raw(EDIT, images=[refs[0], markup], options={"output_format": format_name}), registry
        ).state in READY
    assert validate_request(raw(EDIT, options={"output_format": "gif", "size": "512x512"}), registry).state == "invalid"
    assert validate_request(raw(TEXT, images=[markup]), registry).state == "invalid"
    assert validate_request(raw(EDIT, videos=[markup]), registry).state == "invalid"
    assert validate_request(raw(EDIT, images=[refs[0], {**markup, "media_type": "video"}]), registry).state == "invalid"
    assert validate_request(raw(EDIT, images=[refs[0], {"role": "first_frame", "url": refs[0]}]), registry).state == "invalid"
    assert validate_request(raw(EDIT, images=["asset://provider/ref"]), registry).state == "invalid"
    assert validate_request(raw(EDIT.replace("2-6", "2-5"), images=[refs[0], markup]), registry).state == "invalid"


@pytest.mark.parametrize("override", ["input_urls", "markup", "mask_url"])
def test_normalized_requests_cannot_override_uploaded_fields(override, registry):
    normalized = normalize_request(raw(EDIT, options={override: f"{HOST}/other.png"}), registry)
    with pytest.raises(RequestPreparationError, match="does not support option"):
        build_submission_payload(normalized, registry)


@pytest.mark.parametrize(("role", "provider_field"), [("mask", "mask_url"), ("markup", "markup")])
def test_upload_roles_with_real_client_and_mock_transport(role, provider_field, tmp_path, registry):
    ref = tmp_path / "ref.png"
    aux = tmp_path / "overlay.png"
    Image.new("RGB", (32, 16), "white").save(ref)
    Image.new("RGBA", (32, 16), (255, 0, 0, 0)).save(aux)
    uploads = []

    def respond(request):
        body = request.read()
        is_local = "file-stream-upload" in request.url.path
        if is_local:
            assert b"PNG" in body
        else:
            assert b"https://example.com/second.png" in body
        uploads.append(is_local)
        return httpx.Response(200, json={"success": True, "data": {
            "downloadUrl": f"{HOST}/uploaded-{len(uploads)}.png",
        }})

    settings = KieSettings(api_key="test-key")
    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        upload_client = UploadClient(settings, http_client=http_client)
        prepared = prepare_request_for_submission(
            raw(EDIT, images=[{"path": str(aux), "role": role}, ref, "https://example.com/second.png"]),
            registry, settings=settings, upload_client=upload_client,
        )
    assert uploads == [True, True, False]
    assert prepared.normalized_request.images[0].role == role
    assert prepared.debug["original_media"]["images"][0]["role"] == role
    payload = build_submission_payload(prepared, registry, settings=settings)["input"]
    assert payload[provider_field] == f"{HOST}/uploaded-1.png"
    assert payload["input_urls"] == [f"{HOST}/uploaded-2.png", f"{HOST}/uploaded-3.png"]


def test_local_reference_and_markup_validation_uses_bytes(tmp_path, registry):
    ref = tmp_path / "ref.png"
    overlay = tmp_path / "markup.png"
    Image.new("RGB", (32, 16), "white").save(ref)
    Image.new("RGB", (32, 16), "white").save(overlay, format="JPEG")
    images = [ref, {"role": "markup", "path": str(overlay)}]
    assert "Markup must be a transparent PNG." in validate_request(raw(EDIT, images=images), registry).errors
    Image.new("RGBA", (16, 16), (255, 0, 0, 0)).save(overlay)
    assert "Markup dimensions must match the first reference image." in validate_request(
        raw(EDIT, images=images), registry
    ).errors
    Image.new("RGBA", (32, 16), (255, 0, 0, 255)).save(overlay)
    assert "Markup must be a transparent PNG." in validate_request(raw(EDIT, images=images), registry).errors
    Image.new("RGB", (32, 16)).save(ref, format="GIF")
    assert "Reference image must be JPEG, PNG or WebP." in validate_request(raw(EDIT, images=[ref]), registry).errors
    ref.write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
    assert "Image bytes could not be decoded." in validate_request(raw(EDIT, images=[ref]), registry).errors
    with ref.open("ab") as handle:
        handle.truncate(30 * 1024**2 + 1)
    assert "Reference image exceeds 30 MB." in validate_request(raw(EDIT, images=[ref]), registry).errors


def test_local_mask_requires_alpha_zero_and_alignment(tmp_path, registry):
    ref = tmp_path / "ref.png"
    mask = tmp_path / "mask.png"
    Image.new("RGB", (32, 16), "white").save(ref)
    images = [ref, {"role": "mask", "path": str(mask)}]
    Image.new("1", (32, 16), 0).save(mask)
    result = validate_request(raw(EDIT, images=images), registry)
    assert "Mask must be a PNG or WebP with alpha-zero pixels marking the edit region." in result.errors
    Image.new("RGBA", (32, 16), (0, 0, 0, 127)).save(mask)
    assert validate_request(raw(EDIT, images=images), registry).state == "invalid"
    Image.new("RGBA", (32, 16), (0, 0, 0, 0)).save(mask, format="WEBP")
    assert validate_request(raw(EDIT, images=images), registry).state in READY
    Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(mask)
    assert "Mask dimensions must match the first reference image." in validate_request(
        raw(EDIT, images=images), registry
    ).errors


@pytest.mark.parametrize("key", [EDIT, EDIT.replace("sunburst", "flare")])
def test_local_mask_size_limit_is_inclusive_and_role_specific(key, tmp_path, registry):
    ref = tmp_path / "ref.png"
    mask = tmp_path / "mask.png"
    Image.new("RGB", (16, 16)).save(ref)
    Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(mask)
    byte_limit = 30 * 1024**2
    with mask.open("r+b") as handle:
        handle.truncate(byte_limit)
    assert validate_request(
        raw(key, images=[ref, {"role": "mask", "path": str(mask)}]), registry
    ).state in READY
    with mask.open("r+b") as handle:
        handle.truncate(byte_limit + 1)
    result = validate_request(raw(key, images=[ref, {"role": "mask", "path": str(mask)}]), registry)
    assert result.state == "invalid"
    assert "Mask exceeds 30 MB." in result.errors
    assert validate_request(
        raw(key, images=[ref, {"role": "markup", "path": str(mask)}]), registry
    ).state in READY


def test_pricing_refresh_and_preflight_do_not_use_token_rates_as_estimates(registry):
    snapshot = load_latest_pricing_snapshot()
    current = PricingRegistry(snapshot)
    prior = load_pricing_snapshot_file(
        ROOT / "src/kie_api/resources/pricing/2026-09-09_gpt_image_2_5_market_page.yaml"
    )
    assert all(current.get_rule(rule.model_key) == rule for rule in prior.rules)
    rows = []
    for key in KEYS:
        rule = current.get_rule(key)
        assert rule.billing_unit == "million_tokens"
        assert rule.token_rates["image_output"].credits == 5400
        assert rule.token_rates["cached_text_input"].usd == 1.125
        assert rule.token_rates["svg.gpt-5.6-terra.output"].credits == 2160
        preflight = run_preflight(raw(key, options={"output_format": "svg"}), registry, remaining_credits=50)
        assert preflight.decision == "warn"
        assert preflight.can_submit
        assert not preflight.estimated_cost.is_known
        assert not preflight.estimated_cost.has_numeric_estimate
        assert preflight.estimated_cost.estimated_credits is None
        assert preflight.estimated_cost.estimated_cost_usd is None
        rows.append(PricingCatalogRow(
            model_description=f"{key}, 1K image output", interface_type="image",
            credit_price_text="5400", usd_price_text="27", credit_unit="million tokens",
            anchor=f"https://kie.ai/gpt-image-2-6?model={key}",
        ))
    capture = PricingCatalogCapture(
        page_url="https://kie.ai/pricing", api_base_url="https://api.kie.ai", rows=rows
    )
    refreshed = PricingRegistry(build_supported_model_snapshot(capture, released_on="2026-11-11", registry=registry))
    for key in KEYS:
        assert refreshed.get_rule(key) == current.get_rule(key)
        assert not refreshed.estimate(key, {"resolution": "1K"}).has_numeric_estimate


def encoded_image(format_name, size, *, alpha=None, orientation=None):
    buffer = BytesIO()
    image = Image.new("RGB" if alpha is None else "RGBA", size,
                      (10, 20, 30) if alpha is None else (10, 20, 30, alpha))
    options = {}
    if orientation is not None:
        exif = image.getexif()
        exif[274] = orientation
        options["exif"] = exif
    image.save(buffer, format=format_name, **options)
    return buffer.getvalue()


@pytest.mark.parametrize(("role", "format_name", "provider_field"),
                         [("mask", "WEBP", "mask_url"), ("markup", "PNG", "markup")])
def test_paid_edit_checks_hosted_bytes_and_oriented_alignment(
    role, format_name, provider_field, registry, tmp_path
):
    ref, auxiliary = f"{HOST}/oriented.jpg", f"{HOST}/misleading.txt"
    request = raw(EDIT, images=[ref, {"role": role, "url": auxiliary}])
    validation = validate_request(request, registry)
    assert validation.state == "ready_with_warning"
    assert any(w.code == "remote_image_bytes_unverified" for w in validation.warning_details)
    prepared = PreparedRequest(normalized_request=validation.normalized_request)
    settings = KieSettings(api_key="test-key", download_output_root=str(tmp_path))
    responses = {
        ref: encoded_image("JPEG", (24, 16), orientation=6),
        auxiliary: encoded_image(format_name, (16, 24), alpha=0),
    }
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "GET":
            assert "authorization" not in request.headers and "cookie" not in request.headers
            return httpx.Response(200, content=responses[str(request.url)],
                                  headers={"Content-Type": "application/octet-stream"})
        payload = json.loads(request.content)
        assert payload["input"][provider_field] == auxiliary
        assert payload["input"]["input_urls"] == [ref]
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "mock-task-id"}})

    class PostOnlyAuth(httpx.Auth):
        def auth_flow(self, request):
            assert request.method == "POST"
            yield request

    with httpx.Client(
        transport=httpx.MockTransport(handler), auth=PostOnlyAuth(),
        cookies={"private": "value"}, headers={"Authorization": "default"},
    ) as client:
        submit = SubmitClient(settings, registry, http_client=client)
        assert submit.submit(prepared.normalized_request).task_id == "mock-task-id"
    assert calls == ["GET", "GET", "POST"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("case", "reason"), [
    ("html", "could not be decoded"),
    ("corrupt", "could not be decoded"),
    ("opaque_mask", "alpha-zero"),
    ("unaligned", "dimensions must match"),
    ("opaque_markup", "transparent PNG"),
    ("redirect", "Could not verify"),
    ("too_large", "within the download size limit"),
    ("mask_too_large", r"Could not verify images\[1\] \(mask\)"),
    ("expired", "Could not verify"),
])
def test_paid_edit_rejects_unverified_or_invalid_hosted_content(case, reason, registry, tmp_path):
    ref = f"{HOST}/oriented.jpg"
    aux = f"{HOST}/overlay.png"
    role = "markup" if case == "opaque_markup" else "mask"
    normalized = normalize_request(raw(EDIT, images=[ref, {"role": role, "url": aux}]), registry)
    settings = KieSettings(api_key="test-key", download_output_root=str(tmp_path))
    calls = []

    def handler(request):
        calls.append((request.method, str(request.url)))
        assert request.method == "GET"
        if str(request.url) == ref:
            if case == "too_large":
                return httpx.Response(200, headers={"Content-Length": str(30 * 1024**2 + 1)}, content=b"")
            return httpx.Response(200, content=encoded_image("JPEG", (24, 16), orientation=6))
        assert str(request.url) == aux
        if case == "mask_too_large":
            return httpx.Response(200, headers={"Content-Length": str(30 * 1024**2 + 1)}, content=b"")
        if case == "redirect":
            return httpx.Response(302, headers={"Location": "https://example.com/outside.png"})
        if case == "expired":
            return httpx.Response(404)
        if case == "html":
            return httpx.Response(200, content=b"<html>not an image</html>", headers={"Content-Type": "image/png"})
        if case == "corrupt":
            return httpx.Response(200, content=b"\x89PNG\r\n\x1a\ntruncated")
        if case == "unaligned":
            return httpx.Response(200, content=encoded_image("PNG", (24, 16), alpha=0))
        return httpx.Response(200, content=encoded_image("PNG", (16, 24)))

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        submit = SubmitClient(settings, registry, http_client=client)
        with pytest.raises(RequestPreparationError, match=reason):
            submit.submit(normalized)
    assert calls[0] == ("GET", ref)
    assert len(calls) == (1 if case == "too_large" else 2)
    assert list(tmp_path.iterdir()) == []


def test_preparation_rejects_bad_local_content_even_for_normalized_input(tmp_path, registry):
    spoof = tmp_path / "markup.png"
    spoof.write_bytes(encoded_image("JPEG", (16, 24)))
    normalized = normalize_request(
        raw(EDIT, images=[f"{HOST}/ref.png", {"role": "markup", "path": str(spoof)}]), registry
    )

    def unexpected_upload(_request):
        pytest.fail("an invalid prepared request must not upload")

    settings = KieSettings(api_key="test-key")
    with httpx.Client(transport=httpx.MockTransport(unexpected_upload)) as client:
        with pytest.raises(RequestPreparationError, match="transparent PNG"):
            prepare_request_for_submission(
                normalized, registry, settings=settings, upload_client=UploadClient(settings, http_client=client)
            )
