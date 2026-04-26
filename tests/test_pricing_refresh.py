from kie_api.services.pricing_refresh import (
    PricingCatalogCapture,
    PricingCatalogRow,
    PricingPageCount,
    build_supported_model_snapshot,
    extract_next_data_labels,
    extract_pricing_hints,
)


def test_extract_pricing_hints_finds_public_price_and_credit_lines() -> None:
    html = """
    <div>Starter plan: $12 / month</div>
    <div>Video generation costs 25 credits</div>
    <div>No pricing here</div>
    """

    hints = extract_pricing_hints(html)

    assert "Starter plan: $12 / month" in hints
    assert "Video generation costs 25 credits" in hints


def test_extract_next_data_labels_reads_next_data_pricing_text() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"__namespaces":{"dashboard":{"modelsPricing":{"title":"Pricing","description":"Desc","creditsUnit":"Credits","noteDescription":"Public note","columns":{"creditsPerGenerationInfo":"1 credit ≈ $0.005 USD"}}}}}}}
    </script>
    """

    labels = extract_next_data_labels(html)

    assert labels["title"] == "Pricing"
    assert labels["credits_info"] == "1 credit ≈ $0.005 USD"


def test_build_supported_model_snapshot_maps_live_pricing_rows() -> None:
    count = PricingPageCount.model_validate(
        {"all": 24, "image": 12, "video": 12, "music": 0, "chat": 0}
    )
    row_payloads = [
        {
            "modelDescription": "Google nano banana 2, 4K",
            "interfaceType": "image",
            "provider": "Google",
            "creditPrice": "18",
            "creditUnit": "per image",
            "usdPrice": "0.09",
            "falPrice": "0.16",
            "discountRate": 43.75,
            "anchor": "https://kie.ai/nano-banana-2",
        },
        {
            "modelDescription": "Google nano banana 2, 2K",
            "interfaceType": "image",
            "provider": "Google",
            "creditPrice": "12",
            "creditUnit": "per image",
            "usdPrice": "0.06",
            "falPrice": "0.08",
            "discountRate": 25.0,
            "anchor": "https://kie.ai/nano-banana-2",
        },
        {
            "modelDescription": "Google nano banana 2, 1K",
            "interfaceType": "image",
            "provider": "Google",
            "creditPrice": "8",
            "creditUnit": "per image",
            "usdPrice": "0.04",
            "falPrice": "0.04",
            "discountRate": 0.0,
            "anchor": "https://kie.ai/nano-banana-2",
        },
        {
            "modelDescription": "Google nano banana pro, 1/2K",
            "interfaceType": "image",
            "provider": "Google",
            "creditPrice": "18.0",
            "creditUnit": "per image",
            "usdPrice": "0.09",
            "falPrice": "0.12",
            "discountRate": 25.0,
            "anchor": "https://kie.ai/nano-banana-pro",
        },
        {
            "modelDescription": "Google nano banana pro, 4K",
            "interfaceType": "image",
            "provider": "Google",
            "creditPrice": "24.0",
            "creditUnit": "per image",
            "usdPrice": "0.12",
            "falPrice": "0.16",
            "discountRate": 25.0,
            "anchor": "https://kie.ai/nano-banana-pro",
        },
        {
            "modelDescription": "gpt image 2, image-to-image, 4k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "16",
            "creditUnit": "per image",
            "usdPrice": "0.08",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-image-to-image",
        },
        {
            "modelDescription": "gpt image 2, image-to-image, 2k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "10",
            "creditUnit": "per image",
            "usdPrice": "0.05",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-image-to-image",
        },
        {
            "modelDescription": "gpt image 2, image-to-image, 1k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "6",
            "creditUnit": "per image",
            "usdPrice": "0.03",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-image-to-image",
        },
        {
            "modelDescription": "gpt image 2, text-to-image, 4k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "16",
            "creditUnit": "per image",
            "usdPrice": "0.08",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-text-to-image",
        },
        {
            "modelDescription": "gpt image 2, text-to-image, 2k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "10",
            "creditUnit": "per image",
            "usdPrice": "0.05",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-text-to-image",
        },
        {
            "modelDescription": "gpt image 2, text-to-image, 1k",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "6",
            "creditUnit": "per image",
            "usdPrice": "0.03",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-text-to-image",
        },
        {
            "modelDescription": "gpt image 2, text-to-image, experimental tier",
            "interfaceType": "image",
            "provider": "OpenAI",
            "creditPrice": "99",
            "creditUnit": "per image",
            "usdPrice": "0.495",
            "falPrice": None,
            "discountRate": 0.0,
            "anchor": "https://kie.ai/gpt-image-2?model=gpt-image-2-text-to-image",
        },
        {
            "modelDescription": "kling 2.6, text-to-video, without audio-5.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "55.0",
            "creditUnit": "per video",
            "usdPrice": "0.275",
            "falPrice": "0.3",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Ftext-to-video",
        },
        {
            "modelDescription": "kling 2.6, text-to-video, with audio-5.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "110.0",
            "creditUnit": "per video",
            "usdPrice": "0.55",
            "falPrice": "0.6",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Ftext-to-video",
        },
        {
            "modelDescription": "kling 2.6, text-to-video, without audio-10.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "110.0",
            "creditUnit": "per video",
            "usdPrice": "0.55",
            "falPrice": "0.6",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Ftext-to-video",
        },
        {
            "modelDescription": "kling 2.6, image-to-video, without audio-5.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "55.0",
            "creditUnit": "per video",
            "usdPrice": "0.275",
            "falPrice": "0.3",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Fimage-to-video",
        },
        {
            "modelDescription": "kling 2.6, image-to-video, with audio-5.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "110.0",
            "creditUnit": "per video",
            "usdPrice": "0.55",
            "falPrice": "0.6",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Fimage-to-video",
        },
        {
            "modelDescription": "kling 2.6, image-to-video, without audio-10.0s",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "110.0",
            "creditUnit": "per video",
            "usdPrice": "0.55",
            "falPrice": "0.6",
            "discountRate": 8.33,
            "anchor": "https://kie.ai/kling-2-6?model=kling-2.6%2Fimage-to-video",
        },
        {
            "modelDescription": "kling 3.0, video, with audio-1080P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "27",
            "creditUnit": "per second",
            "usdPrice": "0.135",
            "falPrice": "0.15",
            "discountRate": 10.0,
            "anchor": "https://kie.ai/kling-3-0",
        },
        {
            "modelDescription": "kling 3.0, video, without audio-1080P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "18",
            "creditUnit": "per second",
            "usdPrice": "0.09",
            "falPrice": "0.1",
            "discountRate": 10.0,
            "anchor": "https://kie.ai/kling-3-0",
        },
        {
            "modelDescription": "kling 3.0, video, with audio-720P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "20",
            "creditUnit": "per second",
            "usdPrice": "0.1",
            "falPrice": "0.11",
            "discountRate": 9.09,
            "anchor": "https://kie.ai/kling-3-0",
        },
        {
            "modelDescription": "kling 3.0, video, without audio-720P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "14",
            "creditUnit": "per second",
            "usdPrice": "0.07",
            "falPrice": "0.08",
            "discountRate": 12.5,
            "anchor": "https://kie.ai/kling-3-0",
        },
        {
            "modelDescription": "kling 3.0 motion control, video-to-video, 1080P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "27",
            "creditUnit": "per second",
            "usdPrice": "0.135",
            "falPrice": "0.15",
            "discountRate": 10.0,
            "anchor": "https://kie.ai/kling-3-motion-control",
        },
        {
            "modelDescription": "kling 3.0 motion control, video-to-video, 720P",
            "interfaceType": "video",
            "provider": "Kling",
            "creditPrice": "20",
            "creditUnit": "per second",
            "usdPrice": "0.1",
            "falPrice": "0.11",
            "discountRate": 9.09,
            "anchor": "https://kie.ai/kling-3-motion-control",
        },
        {
            "modelDescription": "bytedance/seedance-2, 720p no video input",
            "interfaceType": "video",
            "provider": "ByteDance",
            "creditPrice": "41",
            "creditUnit": "per second",
            "usdPrice": "0.205",
            "falPrice": "0.25",
            "discountRate": 18.0,
            "anchor": None,
        },
        {
            "modelDescription": "bytedance/seedance-2, 720p with video input",
            "interfaceType": "video",
            "provider": "ByteDance",
            "creditPrice": "25",
            "creditUnit": "per second",
            "usdPrice": "0.125",
            "falPrice": "0.18",
            "discountRate": 30.0,
            "anchor": None,
        },
        {
            "modelDescription": "bytedance/seedance-2, 480p no video input",
            "interfaceType": "video",
            "provider": "ByteDance",
            "creditPrice": "19",
            "creditUnit": "per second",
            "usdPrice": "0.095",
            "falPrice": "0.12",
            "discountRate": 20.0,
            "anchor": None,
        },
        {
            "modelDescription": "bytedance/seedance-2, 480p with video input",
            "interfaceType": "video",
            "provider": "ByteDance",
            "creditPrice": "11.5",
            "creditUnit": "per second",
            "usdPrice": "0.057",
            "falPrice": "0.09",
            "discountRate": 36.0,
            "anchor": None,
        },
    ]

    rows = [
        PricingCatalogRow(
            model_description=item["modelDescription"],
            interface_type=item["interfaceType"],
            provider=item.get("provider"),
            credit_price_text=item.get("creditPrice"),
            credit_unit=item.get("creditUnit"),
            usd_price_text=item.get("usdPrice"),
            fal_price_text=item.get("falPrice"),
            discount_rate=item.get("discountRate"),
            anchor=item.get("anchor"),
            raw_record=item,
        )
        for item in row_payloads
    ]
    capture = PricingCatalogCapture(
        page_url="https://kie.ai/pricing",
        api_base_url="https://api.kie.ai",
        count=count,
        rows=rows,
        ui_labels={"credits_info": "1 credit ≈ $0.005 USD"},
        notes=["live observed"],
    )

    snapshot = build_supported_model_snapshot(capture, released_on="2026-03-26")
    rules = {rule.model_key: rule for rule in snapshot.rules}

    assert snapshot.source_kind == "site_pricing_page_api"
    assert rules["nano-banana-2"].base_credits == 8.0
    assert rules["nano-banana-2"].multipliers["resolution"]["4k"] == 2.25
    assert rules["gpt-image-2-text-to-image"].base_credits == 6.0
    assert rules["gpt-image-2-text-to-image"].base_cost_usd == 0.03
    assert rules["gpt-image-2-text-to-image"].multipliers["resolution"]["2k"] == 10.0 / 6.0
    assert rules["gpt-image-2-text-to-image"].multipliers["resolution"]["4k"] == 16.0 / 6.0
    assert rules["gpt-image-2-image-to-image"].base_credits == 6.0
    assert rules["gpt-image-2-image-to-image"].source_anchor_urls == [
        "https://kie.ai/gpt-image-2?model=gpt-image-2-image-to-image"
    ]
    assert rules["kling-2.6-t2v"].billing_unit == "video"
    assert rules["kling-3.0-t2v"].billing_unit == "second"
    assert rules["kling-3.0-motion"].multipliers["mode"]["1080p"] == 1.35
    assert rules["seedance-2.0"].billing_unit == "second"
    assert rules["seedance-2.0"].multipliers["pricing_variant"]["720p_with_video_input"] == 25.0 / 19.0
    assert snapshot.missing_model_keys == []
    assert "gpt-image-2-text-to-image" in snapshot.priced_model_keys
    assert any(
        row["model_description"] == "gpt image 2, text-to-image, experimental tier"
        for row in snapshot.unmapped_source_rows
    )
