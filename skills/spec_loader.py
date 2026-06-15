"""
Loader for the markdown agent definition files in `agents/` (frontmatter +
instructions, the `.claude/agents/<name>.md` convention). Used to render the agent
roster/cards in the app so the documented team and the running code stay in sync.
"""
from __future__ import annotations

import functools
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
SKILLS_DIR = ROOT / "skills"


def _parse(text: str):
    """Split a markdown file into (frontmatter dict, body)."""
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        return (yaml.safe_load(fm) or {}), body.strip()
    return {}, text.strip()


@functools.lru_cache(maxsize=1)
def load_specs() -> list[dict]:
    """Parse each agents/*.md into {frontmatter fields..., 'prompt': body}."""
    out: list[dict] = []
    for path in sorted(AGENTS_DIR.glob("*.md")):
        meta, body = _parse(path.read_text(encoding="utf-8"))
        spec = dict(meta)
        spec["prompt"] = body
        spec["file"] = f"agents/{path.name}"
        out.append(spec)
    return out


@functools.lru_cache(maxsize=1)
def load_skills() -> list[dict]:
    """Parse each skills/<name>/SKILL.md (anatomy: frontmatter name+description +
    instructions, plus optional scripts/ and reference/). Frontmatter is the always-loaded
    part; the body is shown on demand (progressive disclosure)."""
    out: list[dict] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        folder = skill_md.parent
        meta, body = _parse(skill_md.read_text(encoding="utf-8"))
        files = sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file())
        out.append({"name": meta.get("name", folder.name),
                    "description": meta.get("description", ""),
                    "instructions": body, "folder": f"skills/{folder.name}", "files": files})
    return out
