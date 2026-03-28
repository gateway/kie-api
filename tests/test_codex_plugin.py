import json
from pathlib import Path


def _read_frontmatter_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n"), f"{path} is missing YAML frontmatter"
    _, frontmatter, _ = content.split("---", 2)
    return frontmatter


def test_codex_plugin_manifest_and_marketplace_exist() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    plugin_manifest = repo_root / "plugins" / "kie-ai-workflows" / ".codex-plugin" / "plugin.json"
    marketplace = repo_root / ".agents" / "plugins" / "marketplace.json"

    manifest = json.loads(plugin_manifest.read_text(encoding="utf-8"))
    marketplace_data = json.loads(marketplace.read_text(encoding="utf-8"))

    assert manifest["name"] == "kie-ai-workflows"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["displayName"] == "Kie.ai Workflows"

    assert marketplace_data["plugins"][0]["name"] == "kie-ai-workflows"
    assert marketplace_data["plugins"][0]["source"]["path"] == "./plugins/kie-ai-workflows"


def test_codex_plugin_skills_bundle_exists() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "plugins" / "kie-ai-workflows" / "skills"
    expected = {
        "start-here",
        "check-credits",
        "nano-banana",
        "kling-video",
        "chain-image-to-video",
        "find-latest-media",
    }

    actual = {path.name for path in skills_dir.iterdir() if path.is_dir()}
    assert expected.issubset(actual)

    for skill_name in expected:
        frontmatter = _read_frontmatter_text(skills_dir / skill_name / "SKILL.md")
        assert "name:" in frontmatter
        assert "description:" in frontmatter
