"""Public pricing refresh helpers sourced from KIE's pricing page and site APIs."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ..registry.loader import SpecRegistry, load_registry
from ..registry.models import ModelSpec
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
    registry: Optional[SpecRegistry] = None,
) -> PricingSnapshot:
    released = released_on or date.today().isoformat()
    rules: List[PricingRule] = []
    used_rows: Set[str] = set()
    notes = list(capture.notes)
    notes.append(
        "This snapshot is derived from KIE's public pricing page API and should be treated as non-authoritative."
    )
    resolved_registry = registry or load_registry()

    nano_2_rows = _rows_with_anchor(capture.rows, "https://kie.ai/nano-banana-2")
    if nano_2_rows:
        _mark_rows_used(used_rows, nano_2_rows)
        base = _select_row(nano_2_rows, "1k") or nano_2_rows[0]
        rules.append(_with_row_provenance(
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
                    f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {released}.",
                ],
            ),
            rows=nano_2_rows,
            observed_at=released,
        ))

    nano_pro_rows = _rows_with_anchor(capture.rows, "https://kie.ai/nano-banana-pro")
    if nano_pro_rows:
        _mark_rows_used(used_rows, nano_pro_rows)
        base = nano_pro_rows[0]
        multiplier_4k = _ratio(_credit_for(nano_pro_rows, "4k"), base.credit_price)
        rules.append(_with_row_provenance(
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
                    f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {released}.",
                    "KIE's site pricing groups Nano Banana Pro 1K and 2K into a combined '1/2K' tier.",
                ],
            ),
            rows=nano_pro_rows,
            observed_at=released,
        ))

    kling_26_t2v_rows = _rows_with_phrase(capture.rows, "kling 2.6, text-to-video")
    if kling_26_t2v_rows:
        _mark_rows_used(used_rows, kling_26_t2v_rows)
        rules.append(_build_kling_26_video_rule("kling-2.6-t2v", kling_26_t2v_rows, observed_at=released))

    kling_26_i2v_rows = _rows_with_phrase(capture.rows, "kling 2.6, image-to-video")
    if kling_26_i2v_rows:
        _mark_rows_used(used_rows, kling_26_i2v_rows)
        rules.append(_build_kling_26_video_rule("kling-2.6-i2v", kling_26_i2v_rows, observed_at=released))

    kling_26_motion_rows = _rows_with_anchor(capture.rows, "https://kie.ai/kling-2.6-motion-control")
    if kling_26_motion_rows:
        _mark_rows_used(used_rows, kling_26_motion_rows)
        rules.append(_build_kling_26_motion_rule(kling_26_motion_rows, observed_at=released))

    kling_30_rows = _rows_with_anchor(capture.rows, "https://kie.ai/kling-3-0")
    if kling_30_rows:
        _mark_rows_used(used_rows, kling_30_rows)
        rules.extend(
            [
                _build_kling_30_video_rule("kling-3.0-t2v", kling_30_rows, observed_at=released),
                _build_kling_30_video_rule("kling-3.0-i2v", kling_30_rows, observed_at=released),
            ]
        )

    kling_30_turbo_i2v_rows = _rows_with_phrase(capture.rows, "kling 3.0 turbo, image-to-video")
    if kling_30_turbo_i2v_rows:
        _mark_rows_used(used_rows, kling_30_turbo_i2v_rows)
        rules.append(_build_kling_30_turbo_i2v_rule(kling_30_turbo_i2v_rows, observed_at=released))

    kling_30_motion_rows = _rows_with_anchor(capture.rows, "https://kie.ai/kling-3-motion-control")
    if kling_30_motion_rows:
        _mark_rows_used(used_rows, kling_30_motion_rows)
        rules.append(_build_kling_30_motion_rule(kling_30_motion_rows, observed_at=released))

    seedance_rows = _rows_with_phrase(capture.rows, "bytedance/seedance-2,")
    if seedance_rows:
        _mark_rows_used(used_rows, seedance_rows)
        rules.append(_build_seedance_2_rule(seedance_rows, observed_at=released))

    seedance_fast_rows = _rows_with_phrase(capture.rows, "bytedance/seedance-2 fast,")
    if seedance_fast_rows:
        _mark_rows_used(used_rows, seedance_fast_rows)
        rules.append(
            _build_seedance_2_rule(
                seedance_fast_rows,
                model_key="seedance-2.0-fast",
                anchor_url="https://kie.ai/seedance-2-0?model=bytedance%2Fseedance-2-fast",
                observed_at=released,
            )
        )

    seedance_mini_rows = _rows_with_phrase(capture.rows, "bytedance/seedance-2-mini,")
    if seedance_mini_rows:
        _mark_rows_used(used_rows, seedance_mini_rows)
        rules.append(
            _build_seedance_2_rule(
                seedance_mini_rows,
                model_key="seedance-2.0-mini",
                anchor_url="https://kie.ai/seedance-2-0-mini",
                observed_at=released,
            )
        )

    existing_model_keys = {rule.model_key for rule in rules}
    for spec in sorted(resolved_registry.iter_models(), key=lambda item: item.key):
        if spec.key in existing_model_keys:
            continue
        image_rows = _rows_matching_model_spec(capture.rows, spec)
        image_rule = _build_generic_image_resolution_rule(
            spec,
            image_rows,
            observed_at=released,
        )
        if image_rule:
            _mark_rows_used(
                used_rows,
                [row for row in image_rows if row.model_description in image_rule.source_row_labels],
            )
            rules.append(image_rule)
            existing_model_keys.add(spec.key)

    if (
        "suno-generate-music" not in existing_model_keys
        and resolved_registry.model_specs.get("suno-generate-music")
    ):
        rules.append(
            PricingRule(
                model_key="suno-generate-music",
                pricing_status="unknown",
                billing_unit="request",
                provider="Suno",
                interface_type="music",
                anchor_url="https://docs.kie.ai/suno-api/generate-music",
                notes=[
                    "Suno pricing is intentionally marked unknown until verified KIE pricing rows are available.",
                    f"No matching KIE site pricing row was observed on {released}.",
                ],
            )
        )
        existing_model_keys.add("suno-generate-music")

    priced_model_keys = sorted({rule.model_key for rule in rules})
    supported_model_keys = sorted(spec.key for spec in resolved_registry.iter_models())

    return PricingSnapshot(
        version=f"{released}-site-pricing-page",
        label="KIE site pricing page snapshot",
        released_on=released,
        currency="USD",
        source_kind="site_pricing_page_api",
        source_url=capture.page_url,
        notes=notes,
        rules=rules,
        priced_model_keys=priced_model_keys,
        missing_model_keys=[
            key for key in supported_model_keys if key not in set(priced_model_keys)
        ],
        unmapped_source_rows=[
            _row_public_payload(row)
            for row in capture.rows
            if _row_key(row) not in used_rows and _row_is_relevant_to_registry(row, resolved_registry)
        ],
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


def _build_kling_26_video_rule(
    model_key: str,
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "without audio-5.0s") or rows[0]
    return _with_row_provenance(
        PricingRule(
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
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _build_kling_26_motion_rule(
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "720p") or rows[0]
    mode_multiplier = _ratio(_credit_for(rows, "1080p"), base.credit_price)
    return _with_row_provenance(
        PricingRule(
            model_key="kling-2.6-motion",
            pricing_status="observed_site_pricing",
            billing_unit="second",
            provider="Kling",
            interface_type="video",
            anchor_url="https://kie.ai/kling-2.6-motion-control",
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
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _build_kling_30_video_rule(
    model_key: str,
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "without audio-720p") or rows[0]
    return _with_row_provenance(
        PricingRule(
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
                "duration": {str(value): float(value) for value in range(3, 16)},
                "pricing_variant": {
                    "720p_false": 1.0,
                    "720p_true": _ratio(_credit_for(rows, "with audio-720p"), base.credit_price),
                    "1080p_false": _ratio(_credit_for(rows, "without audio-1080p"), base.credit_price),
                    "1080p_true": _ratio(_credit_for(rows, "with audio-1080p"), base.credit_price),
                    "4k_false": _ratio(_credit_for(rows, "without audio-4k"), base.credit_price),
                    "4k_true": _ratio(_credit_for(rows, "with audio-4k"), base.credit_price),
                },
            },
            notes=[
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
                "The site pricing page does not distinguish Kling 3.0 text-to-video from image-to-video pricing.",
                "Kling 3.0 video pricing is modeled with an internal pricing_variant derived from mode plus sound because 4K rows do not add a separate audio surcharge.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _build_kling_30_motion_rule(
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "720p") or rows[0]
    mode_multiplier = _ratio(_credit_for(rows, "1080p"), base.credit_price)
    return _with_row_provenance(
        PricingRule(
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
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _build_kling_30_turbo_i2v_rule(
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "720p") or rows[0]
    return _with_row_provenance(
        PricingRule(
            model_key="kling-3.0-turbo-i2v",
            pricing_status="observed_site_pricing",
            billing_unit="second",
            provider="Kling",
            interface_type="video",
            anchor_url="https://kie.ai/kling-3-0-turbo?model=kling%2Fv3-turbo-image-to-video",
            raw_credit_text=base.credit_price_text,
            raw_usd_text=base.usd_price_text,
            base_credits=base.credit_price,
            base_cost_usd=base.usd_price,
            multipliers={
                "duration": {str(value): float(value) for value in range(3, 16)},
                "resolution": {
                    "720p": 1.0,
                    "1080p": _ratio(_credit_for(rows, "1080p"), base.credit_price),
                },
            },
            notes=[
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
                "Kling 3.0 Turbo image-to-video pricing is modeled by duration and output resolution.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _build_seedance_2_rule(
    rows: List[PricingCatalogRow],
    *,
    model_key: str = "seedance-2.0",
    anchor_url: str = "https://kie.ai/seedance-2-0",
    observed_at: str,
) -> PricingRule:
    base = _select_row(rows, "480p no video input") or _select_row(rows, "480p no video") or rows[0]
    pricing_variant = {
        "480p_no_video_input": 1.0,
        "720p_no_video_input": _ratio(_seedance_credit_for(rows, "720p", with_video=False), base.credit_price),
        "480p_with_video_input": _ratio(_seedance_credit_for(rows, "480p", with_video=True), base.credit_price),
        "720p_with_video_input": _ratio(_seedance_credit_for(rows, "720p", with_video=True), base.credit_price),
    }
    if _select_row(rows, "1080p no video input") or _select_row(rows, "1080p no video"):
        pricing_variant["1080p_no_video_input"] = _ratio(
            _seedance_credit_for(rows, "1080p", with_video=False),
            base.credit_price,
        )
    if _select_row(rows, "1080p with video input") or _select_row(rows, "1080p with video"):
        pricing_variant["1080p_with_video_input"] = _ratio(
            _seedance_credit_for(rows, "1080p", with_video=True),
            base.credit_price,
        )

    return _with_row_provenance(
        PricingRule(
            model_key=model_key,
            pricing_status="observed_site_pricing",
            billing_unit="second",
            provider="ByteDance",
            interface_type="video",
            anchor_url=anchor_url,
            raw_credit_text=base.credit_price_text,
            raw_usd_text=base.usd_price_text,
            base_credits=base.credit_price,
            base_cost_usd=base.usd_price,
            multipliers={
                "duration": {str(value): float(value) for value in range(4, 16)},
                "pricing_variant": pricing_variant,
            },
            notes=[
                f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
                "Seedance pricing is modeled with an internal pricing_variant derived from request resolution plus whether reference_video_urls are present.",
                "The site pricing API publishes separate rows for 'with video input' and 'no video input'; this rule maps those exactly for dry-run estimation.",
            ],
        ),
        rows=rows,
        observed_at=observed_at,
    )


def _seedance_credit_for(
    rows: List[PricingCatalogRow],
    resolution: str,
    *,
    with_video: bool,
) -> Optional[float]:
    row = _select_row(rows, f"{resolution} {'with video' if with_video else 'no video'}")
    return row.credit_price if row else None


def _build_generic_image_resolution_rule(
    spec: ModelSpec,
    rows: List[PricingCatalogRow],
    *,
    observed_at: str,
) -> Optional[PricingRule]:
    image_rows = [
        row
        for row in rows
        if row.interface_type.lower() == "image"
        and row.credit_price is not None
        and _row_resolution(row) is not None
    ]
    if not image_rows:
        return None

    base = _select_resolution_row(image_rows, "1k") or image_rows[0]
    if base.credit_price in (None, 0):
        return None

    multipliers: Dict[str, float] = {}
    for resolution in ("1k", "2k", "4k"):
        row = _select_resolution_row(image_rows, resolution)
        if row and row.credit_price is not None:
            multipliers[resolution] = _ratio(row.credit_price, base.credit_price)

    notes = [
        f"Observed from https://api.kie.ai/client/v1/model-pricing/page on {observed_at}.",
        "Mapped by matching KIE pricing rows to the model registry and image resolution labels.",
    ]
    if set(multipliers) != {"1k", "2k", "4k"}:
        notes.append("KIE pricing rows did not expose every common 1K/2K/4K resolution tier.")

    return _with_row_provenance(
        PricingRule(
            model_key=spec.key,
            pricing_status="observed_site_pricing",
            billing_unit="request",
            provider=base.provider,
            interface_type=base.interface_type,
            anchor_url=base.anchor,
            raw_credit_text=base.credit_price_text,
            raw_usd_text=base.usd_price_text,
            base_credits=base.credit_price,
            base_cost_usd=base.usd_price,
            multipliers={"resolution": multipliers} if multipliers else {},
            notes=notes,
        ),
        rows=image_rows,
        observed_at=observed_at,
    )


def _rows_matching_model_spec(rows: List[PricingCatalogRow], spec: ModelSpec) -> List[PricingCatalogRow]:
    expected_values = {
        _normalize_match_text(spec.key),
        _normalize_match_text(spec.provider_model),
        _normalize_match_text(spec.label),
    }
    expected_values = {value for value in expected_values if value}
    matches = []
    for row in rows:
        row_model = _anchor_model_value(row.anchor)
        if row_model and row_model in {spec.key, spec.provider_model}:
            matches.append(row)
            continue
        description = _normalize_match_text(row.model_description)
        anchor = _normalize_match_text(row.anchor or "")
        if any(value and (value in description or value in anchor) for value in expected_values):
            matches.append(row)
    return matches


def _anchor_model_value(anchor: Optional[str]) -> Optional[str]:
    if not anchor:
        return None
    parsed = urlparse(anchor)
    model_values = parse_qs(parsed.query).get("model")
    if not model_values:
        return None
    return unquote(model_values[0]).strip() or None


def _normalize_match_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _row_resolution(row: PricingCatalogRow) -> Optional[str]:
    description = row.model_description.lower()
    for resolution in ("1k", "2k", "4k"):
        if re.search(rf"(^|[^a-z0-9]){resolution}([^a-z0-9]|$)", description):
            return resolution
    return None


def _select_resolution_row(
    rows: List[PricingCatalogRow],
    resolution: str,
) -> Optional[PricingCatalogRow]:
    for row in rows:
        if _row_resolution(row) == resolution:
            return row
    return None


def _with_row_provenance(
    rule: PricingRule,
    *,
    rows: List[PricingCatalogRow],
    observed_at: str,
) -> PricingRule:
    return rule.model_copy(
        update={
            "observed_at": observed_at,
            "source_row_labels": sorted({row.model_description for row in rows if row.model_description}),
            "source_anchor_urls": sorted({row.anchor for row in rows if row.anchor}),
        }
    )


def _mark_rows_used(used_rows: Set[str], rows: List[PricingCatalogRow]) -> None:
    for row in rows:
        used_rows.add(_row_key(row))


def _row_key(row: PricingCatalogRow) -> str:
    return "|".join(
        [
            row.model_description,
            row.interface_type,
            row.provider or "",
            row.credit_price_text or "",
            row.usd_price_text or "",
            row.anchor or "",
        ]
    )


def _row_public_payload(row: PricingCatalogRow) -> Dict[str, Any]:
    return {
        "model_description": row.model_description,
        "interface_type": row.interface_type,
        "provider": row.provider,
        "credit_price_text": row.credit_price_text,
        "usd_price_text": row.usd_price_text,
        "anchor": row.anchor,
    }


def _row_is_relevant_to_registry(row: PricingCatalogRow, registry: SpecRegistry) -> bool:
    row_model = _anchor_model_value(row.anchor)
    if row_model and any(
        row_model in {spec.key, spec.provider_model} for spec in registry.iter_models()
    ):
        return True
    row_text = _normalize_match_text(" ".join([row.model_description, row.anchor or ""]))
    return any(
        _normalize_match_text(spec.key) in row_text
        or _normalize_match_text(spec.provider_model) in row_text
        or _normalize_match_text(spec.label) in row_text
        for spec in registry.iter_models()
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
