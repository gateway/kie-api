import json
from pathlib import Path

from kie_api.services.pricing_refresh import (
    PricingCatalogCapture,
    PricingCatalogRow,
    PricingPageCount,
    build_supported_model_snapshot,
    extract_next_data_labels,
    extract_pricing_hints,
)


FIXTURES_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "live_responses"
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
        json.loads((FIXTURES_DIR / "pricing_count_2026-03-26.json").read_text())["data"]
    )
    row_payloads = []
    for name in ("pricing_nano_banana_2026-03-26.json", "pricing_kling_2026-03-26.json"):
        row_payloads.extend(json.loads((FIXTURES_DIR / name).read_text())["data"]["records"])

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
    assert rules["kling-2.6-t2v"].billing_unit == "video"
    assert rules["kling-3.0-t2v"].billing_unit == "second"
    assert rules["kling-3.0-motion"].multipliers["mode"]["1080p"] == 1.35
