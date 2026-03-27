#!/usr/bin/env python3
"""Install repo-bundled Codex skills into the user's local Codex skills folder."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    source_root = repo_root / "agent_skills" / "codex"
    target_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"

    if not source_root.exists():
        raise SystemExit(f"Source skills folder not found: {source_root}")

    target_root.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_dir in sorted(p for p in source_root.iterdir() if p.is_dir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        destination = target_root / skill_dir.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(skill_dir, destination)
        installed.append(destination)

    print("Installed Codex skills:")
    for path in installed:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
