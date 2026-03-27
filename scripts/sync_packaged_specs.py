#!/usr/bin/env python3
"""Sync or check bundled package model specs against the editable source specs."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if bundled package specs differ from source specs.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "specs" / "models"
    bundled_dir = repo_root / "src" / "kie_api" / "resources" / "specs" / "models"

    source_files = sorted(source_dir.glob("*.yaml"))
    bundled_files = sorted(bundled_dir.glob("*.yaml"))

    if args.check:
        return check_sync(source_files, bundled_files)

    bundled_dir.mkdir(parents=True, exist_ok=True)
    for source_file in source_files:
        shutil.copy2(source_file, bundled_dir / source_file.name)
    print(f"Synced {len(source_files)} model specs into {bundled_dir}")
    return 0


def check_sync(source_files, bundled_files) -> int:
    source_names = [path.name for path in source_files]
    bundled_names = [path.name for path in bundled_files]
    if source_names != bundled_names:
        print("Bundled model spec file set differs from source specs.", file=sys.stderr)
        print(f"source={source_names}", file=sys.stderr)
        print(f"bundled={bundled_names}", file=sys.stderr)
        return 1

    for source_file in source_files:
        bundled_file = source_file.parents[2] / "src" / "kie_api" / "resources" / "specs" / "models" / source_file.name
        if source_file.read_text(encoding="utf-8") != bundled_file.read_text(encoding="utf-8"):
            print(f"Bundled model spec drift detected for {source_file.name}", file=sys.stderr)
            return 1
    print("Bundled model specs are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
