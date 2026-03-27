"""Public pricing refresh helpers sourced from KIE's pricing page and site APIs."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ..registry.models import PricingRule, PricingSnapshot


SITE_PRICING_PAGE_URL = "https://kie.ai/pricing"
SITE_PRICING_API_BASE_URL = "https://api.kie.ai"
SITE_PRICING_COUNT_PATH = "/client/v1/model-pricing/count"
SITE_PRICING_PAGE_PATH = "/client/v1/model-pricing/page"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)


class PricingHintCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_url: str
    matched_lines: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class PricingPageCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all: int = 0
    image: int = 0
    video: int = 0
    music: int = 0
    chat: int = 0


class PricingCatalogRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_description: str
    interface_type: str
    provider: Optional[str] = None
    credit_price_text: Optional[str] = None
    credit_unit: Optional[str] = None
    usd_price_text: Optional[str] = None
    fal_price_text: Optional[str] = None
    discount_rate: Optional[float] = None
    anchor: Optional[str] = None
    raw_record: Dict[str, object] = Field(default_factory=dict)

    @property
    def credit_price(self) -> Optional[float]:
        return _coerce_float(self.credit_price_text)

    @property
    def usd_price(self) -> Optional[float]:
        return _coerce_float(self.usd_price_text)


class PricingCatalogCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_url: str
    api_base_url: str
    count: Optional[PricingPageCount] = None
    rows: List[PricingCatalogRow] = Field(default_factory=list)
    ui_labels: Dict[str, str] = Field(default_factory=dict)
    matched_lines: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


def fetch_pricing_hint_capture(
    page_url: str,
    http_client: Optional[httpx.Client] = None,
) -> PricingHintCapture:
    client = http_client or _build_client()
    response = client.get(page_url)
    response.raise_for_status()
    return PricingHintCapture(
        page_url=page_url,
        matched_lines=extract_pricing_hints(response.text),
        notes=[
            "Best-effort public-page scrape only. Prefer the structured site pricing API when available.",
        ],
    )


def fetch_site_pricing_catalog(
    *,
    page_url: str = SITE_PRICING_PAGE_URL,
    api_base_url: str = SITE_PRICING_API_BASE_URL,
    page_size: int = 100,
    http_client: Optional[httpx.Client] = None,
) -> PricingCatalogCapture:
    client = http_client or _build_client()
    html_response = client.get(page_url)
    html_response.raise_for_status()
    html = html_response.text

    count_response = client.get(f"{api_base_url}{SITE_PRICING_COUNT_PATH}")
    count_response.raise_for_status()
    count_payload = count_response.json()
    count_data = count_payload.get("data") or {}
    count = PricingPageCount.model_validate(count_data)

    rows: List[PricingCatalogRow] = []
    total_pages = max(1, (count.all + page_size - 1) // page_size)
    for page_num in range(1, total_pages + 1):
        response = client.post(
            f"{api_base_url}{SITE_PRICING_PAGE_PATH}",
            json={"pageNum": page_num, "pageSize": page_size},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        for record in data.get("records") or []:
            rows.append(
                PricingCatalogRow(
                    model_description=str(record.get("modelDescription") or ""),
                    interface_type=str(record.get("interfaceType") or ""),
                    provider=_coerce_optional_str(record.get("provider")),
                    credit_price_text=_coerce_optional_str(record.get("creditPrice")),
                    credit_unit=_coerce_optional_str(record.get("creditUnit")),
                    usd_price_text=_coerce_optional_str(record.get("usdPrice")),
                    fal_price_text=_coerce_optional_str(record.get("falPrice")),
                    discount_rate=_coerce_float(record.get("discountRate")),
                    anchor=_coerce_optional_str(record.get("anchor")),
                    raw_record=record,
                )
            )

    return PricingCatalogCapture(
        page_url=page_url,
        api_base_url=api_base_url,
        count=count,
        rows=rows,
        ui_labels=extract_next_data_labels(html),
        matched_lines=extract_pricing_hints(html),
        notes=[
            "Pricing rows were fetched from KIE's public site pricing API, discovered from the pricing page bundle.",
            "Treat this as live-observed site pricing, not provider-authoritative billing truth.",
        ],
    )


def build_supported_model_snapshot(
    capture: PricingCatalogCapture,
    *,
    released_on: Optional[str] = None,
) -> PricingSnapshot:
    released = released_on or date.today().isoformat()
    rules: List[PricingRule] = []
    notes = list(capture.notes)
    notes.append(
        "This snapshot is derived from KIE's public pricing page API and should be treated as non-authoritative."
    )

    nano_2_rows = _rows_with_anchor(capture.rows, "https://kie.ai/nano-banana-2")
    if nano_2_rows:
        base = _select_row(nano_2_rows, "1k") or nano_2_rows[0]
        rules.append(
            PricingRule(
                model_key="nano-banana-2",
                pricing_status="observed_site_pricing",
                billing_unit="request",
                provider="Google",
                interface_type="image",
                anchor_url="https://kie.ai/nano-banana-2",
                raw_credit_text=base.credit_price_text,
                raw_usd_text=base.usd_price_text,
                base_credits=base.credit_price,
                base_cost_usd=base.usd_price,
                multipliers={
                    "resolution": {
                        "1k": 1.0,
                        "2k": _ratio(_credit_for(nano_2_rows, "2k"), base.credit_price),
                        "4k": _ratio(_credit_for(nano_2_rows, "4k"), base.credit_price),
                    }
                },
                notes=[
                    "Observed from https://api.kie.ai/client/v1/model-pricing/page on 2026-03-26.",
                ],
            )
        )

    nano_pro_rows = _rows_with_anchor(capture.rows, "https://kie.ai/nano-banana-pro")
    if nano_pro_rows:
        base = nano_pro_rows[0]
        multiplier_4k = _ratio(_credit_for(nano_pro_rows, "4k"), base.credit_price)
        rules.append(
            PricingRule(
                model_key="nano-banana-pro",
                pricing_status="observed_site_pricing",
                billing_unit="request",
                provider="Google",
                interface_type="image",
                anchor_url="https://kie.ai/nano-banana-pro",
                raw_credit_text=base.credit_price_text,
                raw_usd_text=base.usd_price_text,
                base_credits=base.credit_price,
                base_cost_usd=base.usd_price,
                multipliers={
                    "resolution": {
                        "1k": 1.0,
                        "2k": 1.0,
                        "4k": multiplier_4k,
                    }
                },
                notes=[
                    "Observed from https://api.kie.ai/client/v1/model-pricing/page on 2026-03-26.",
                    "KIE's site pricing groups Nano Banana Pro 1K and 2K into a combined '1/2K' tier.",
                ],
            )
        )

    kling_26_t2v_rows = _rows_with_phrase(capture.rows, "kling 2.6, text-to-video")
    if kling_26_t2v_rows:
        rules.append(_build_kling_26_video_rule("kling-2.6-t2v", kling_26_t2v_rows))

    kling_26_i2v_rows = _rows_with_phrase(capture.rows, "kling 2.6, image-to-video")
    if kling_26_i2v_rows:
        rules.append(_build_kling_26_video_rule("kling-2.6-i2v", kling_26_i2v_rows))

    kling_30_rows = _rows_with_anchor(capture.rows, "https://kie.ai/kling-3-0")
    if kling_30_rows:
        rules.extend(
            [
                _build_kling_30_video_rule("kling-3.0-t2v", kling_30_rows),
                _build_kling_30_video_rule("kling-3.0-i2v", kling_30_rows),
            ]
        )

    kling_30_motion_rows = _rows_with_anchor(capture.rows, "https://kie.ai/kling-3-motion-control")
    if kling_30_motion_rows:
        rules.append(_build_kling_30_motion_rule(kling_30_motion_rows))

    return PricingSnapshot(
        version=f"{released}-site-pricing-page",
        label="KIE site pricing page snapshot",
        released_on=released,
        currency="USD",
        source_kind="site_pricing_page_api",
        source_url=capture.page_url,
        notes=notes,
        rules=rules,
    )


def extract_pricing_hints(html: str) -> List[str]:
    results: List[str] = []
    for line in html.splitlines():
        cleaned = " ".join(line.split())
        cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
        if not cleaned:
            continue
        if re.search(r"\$\s*\d", cleaned) or re.search(r"\b\d+(\.\d+)?\s*credits?\b", cleaned, re.I):
            results.append(cleaned)
    return results


def extract_next_data_labels(html: str) -> Dict[str, str]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        return {}
    data = json.loads(match.group(1))
    pricing = (
        data.get("props", {})
        .get("pageProps", {})
        .get("__namespaces", {})
        .get("dashboard", {})
        .get("modelsPricing", {})
    )
    columns = pricing.get("columns") or {}
    labels = {
        "title": pricing.get("title"),
        "description": pricing.get("description"),
        "credits_unit": pricing.get("creditsUnit"),
        "credits_info": columns.get("creditsPerGenerationInfo"),
        "note": pricing.get("noteDescription"),
    }
    return {key: value for key, value in labels.items() if value}


def _build_client() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        headers={"User-Agent": CHROME_USER_AGENT},
    )


def _rows_with_anchor(rows: List[PricingCatalogRow], anchor: str) -> List[PricingCatalogRow]:
    return [row for row in rows if row.anchor == anchor]


def _rows_with_phrase(rows: List[PricingCatalogRow], phrase: str) -> List[PricingCatalogRow]:
    lowered = phrase.lower()
    return [row for row in rows if lowered in row.model_description.lower()]


def _select_row(rows: List[PricingCatalogRow], needle: str) -> Optional[PricingCatalogRow]:
    lowered = needle.lower()
    for row in rows:
        if lowered in row.model_description.lower():
            return row
    return None


def _credit_for(rows: List[PricingCatalogRow], needle: str) -> Optional[float]:
    row = _select_row(rows, needle)
    return row.credit_price if row else None


def _cost_for(rows: List[PricingCatalogRow], needle: str) -> Optional[float]:
    row = _select_row(rows, needle)
    return row.usd_price if row else None


def _ratio(value: Optional[float], base: Optional[float]) -> float:
    if value is None or base in (None, 0):
        return 1.0
    return float(value) / float(base)


def _build_kling_26_video_rule(model_key: str, rows: List[PricingCatalogRow]) -> PricingRule:
    base = _select_row(rows, "without audio-5.0s") or rows[0]
    return PricingRule(
        model_key=model_key,
        pricing_status="observed_site_pricing",
        billing_unit="video",
        provider="Kling",
        interface_type="video",
        anchor_url=base.anchor,
        raw_credit_text=base.credit_price_text,
        raw_usd_text=base.usd_price_text,
        base_credits=base.credit_price,
        base_cost_usd=base.usd_price,
        multipliers={
            "duration": {
                "5": 1.0,
                "10": _ratio(_credit_for(rows, "without audio-10.0s"), base.credit_price),
            },
            "sound": {
                "false": 1.0,
                "true": _ratio(_credit_for(rows, "with audio-5.0s"), base.credit_price),
            },
        },
        notes=[
            "Observed from https://api.kie.ai/client/v1/model-pricing/page on 2026-03-26.",
        ],
    )


def _build_kling_30_video_rule(model_key: str, rows: List[PricingCatalogRow]) -> PricingRule:
    base = _select_row(rows, "without audio-720p") or rows[0]
    mode_multiplier = _ratio(_credit_for(rows, "without audio-1080p"), base.credit_price)
    sound_multiplier = _ratio(_credit_for(rows, "with audio-720p"), base.credit_price)
    return PricingRule(
        model_key=model_key,
        pricing_status="observed_site_pricing",
        billing_unit="second",
        provider="Kling",
        interface_type="video",
        anchor_url="https://kie.ai/kling-3-0",
        raw_credit_text=base.credit_price_text,
        raw_usd_text=base.usd_price_text,
        base_credits=base.credit_price,
        base_cost_usd=base.usd_price,
        multipliers={
            "duration": {"5": 5.0, "10": 10.0},
            "mode": {
                "std": 1.0,
                "pro": mode_multiplier,
                "720p": 1.0,
                "1080p": mode_multiplier,
            },
            "sound": {
                "false": 1.0,
                "true": sound_multiplier,
            },
        },
        notes=[
            "Observed from https://api.kie.ai/client/v1/model-pricing/page on 2026-03-26.",
            "The site pricing page does not distinguish Kling 3.0 text-to-video from image-to-video pricing.",
        ],
    )


def _build_kling_30_motion_rule(rows: List[PricingCatalogRow]) -> PricingRule:
    base = _select_row(rows, "720p") or rows[0]
    mode_multiplier = _ratio(_credit_for(rows, "1080p"), base.credit_price)
    return PricingRule(
        model_key="kling-3.0-motion",
        pricing_status="observed_site_pricing",
        billing_unit="second",
        provider="Kling",
        interface_type="video",
        anchor_url="https://kie.ai/kling-3-motion-control",
        raw_credit_text=base.credit_price_text,
        raw_usd_text=base.usd_price_text,
        base_credits=base.credit_price,
        base_cost_usd=base.usd_price,
        multipliers={
            "duration": {"5": 5.0, "10": 10.0},
            "mode": {
                "720p": 1.0,
                "1080p": mode_multiplier,
                "std": 1.0,
                "pro": mode_multiplier,
            },
        },
        notes=[
            "Observed from https://api.kie.ai/client/v1/model-pricing/page on 2026-03-26.",
        ],
    )


def _coerce_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _coerce_optional_str(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)
