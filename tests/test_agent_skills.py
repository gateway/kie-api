from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} is missing YAML frontmatter"
    _, frontmatter, _ = text.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert isinstance(data, dict), f"{path} frontmatter did not parse to a dict"
    return data


def test_codex_skill_bundles_have_required_files() -> None:
    skill_root = REPO_ROOT / "agent_skills" / "codex"
    skill_dirs = sorted(path for path in skill_root.iterdir() if path.is_dir())
    assert skill_dirs

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md for {skill_dir.name}"
        frontmatter = _load_frontmatter(skill_file)
        assert frontmatter.get("name")
        assert frontmatter.get("description")


def test_claude_agents_have_required_frontmatter() -> None:
    agent_root = REPO_ROOT / ".claude" / "agents"
    agent_files = sorted(agent_root.glob("*.md"))
    assert agent_files

    for agent_file in agent_files:
        frontmatter = _load_frontmatter(agent_file)
        assert frontmatter.get("name")
        assert frontmatter.get("description")
