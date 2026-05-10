"""Fail CI when public release hygiene rules are violated."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BLOCKED_TRACKED_PATHS = {
    "docs/LIVE_VERIFICATION_REPORT.md",
    "docs/MATURITY_MAP.md",
    "docs/REAL_API_INTEGRATION_READINESS.md",
}

BLOCKED_TRACKED_PREFIXES = (
    "docs/planning/",
    "docs/reviews/",
    "outputs/",
    "fixtures/live_responses/",
)

SENSITIVE_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"E:\\Development", re.IGNORECASE),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
)

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".example",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_text_path(path: str) -> bool:
    suffixes = Path(path).suffixes
    if not suffixes:
        return True
    return any(suffix in TEXT_SUFFIXES for suffix in suffixes)


def main() -> int:
    tracked = git_ls_files()
    failures: list[str] = []

    for path in tracked:
        if path in BLOCKED_TRACKED_PATHS or path.startswith(BLOCKED_TRACKED_PREFIXES):
            failures.append(f"blocked tracked path: {path}")

    for path in tracked:
        if not is_text_path(path):
            continue
        full_path = ROOT / path
        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(content):
                failures.append(f"sensitive pattern {pattern.pattern!r} in {path}")

    if failures:
        print("Repository hygiene check failed:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
