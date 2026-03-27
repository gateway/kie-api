#!/usr/bin/env python3
"""Fetch KIE's public site pricing data and emit a candidate pricing snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from kie_api.services.pricing_refresh import build_supported_model_snapshot, fetch_site_pricing_catalog


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump(exclude_none=True))
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh a KIE pricing snapshot from the public pricing page APIs."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the candidate snapshot YAML to this path instead of stdout.",
    )
    parser.add_argument(
        "--released-on",
        help="Override the released_on date embedded in the snapshot (YYYY-MM-DD).",
    )
    args = parser.parse_args()

    capture = fetch_site_pricing_catalog()
    snapshot = build_supported_model_snapshot(capture, released_on=args.released_on)
    text = yaml.safe_dump(_to_plain(snapshot), sort_keys=False)

    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
