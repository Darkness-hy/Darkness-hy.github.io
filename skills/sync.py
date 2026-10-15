#!/usr/bin/env python3
"""Snapshot workspace skills into the GitHub Pages /skills catalog.

Source of truth: <workspace>/assets/skills/<name>/SKILL.md
Published copies:  skills/library/<name>/SKILL.md
Index:             skills/catalog.json
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
WORKSPACE = SITE_ROOT.parent
SOURCE = WORKSPACE / "assets" / "skills"
LIBRARY = HERE / "library"
CATALOG = HERE / "catalog.json"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    return parse_simple_yaml(match.group(1)), match.group(2).lstrip("\n")


def parse_simple_yaml(block: str) -> dict:
    """Parse the shallow YAML used in SKILL.md frontmatter (scalars, lists, one nested map)."""
    root: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#") or line.startswith(" "):
            i += 1
            continue
        key, sep, remainder = line.partition(":")
        if not sep:
            i += 1
            continue
        key = key.strip()
        remainder = remainder.strip()
        if remainder:
            root[key] = coerce(remainder)
            i += 1
            continue
        i += 1
        if i < len(lines) and lines[i].lstrip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(coerce(lines[i].lstrip()[2:].strip()))
                i += 1
            root[key] = items
        elif i < len(lines) and lines[i].startswith("  "):
            nested: dict = {}
            while i < len(lines) and lines[i].startswith("  ") and not lines[i].lstrip().startswith("- "):
                nested_line = lines[i].strip()
                if nested_line and not nested_line.startswith("#"):
                    nested_key, nested_sep, nested_rest = nested_line.partition(":")
                    if nested_sep:
                        nested[nested_key.strip()] = coerce(nested_rest.strip())
                i += 1
            root[key] = nested
        else:
            root[key] = {}
    return root


def coerce(value: str):
    if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def collect_skills() -> list[dict]:
    if not SOURCE.is_dir():
        raise SystemExit(f"skill source not found: {SOURCE}")

    skills = []
    for skill_dir in sorted(path for path in SOURCE.iterdir() if path.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        name = str(meta.get("name") or skill_dir.name)
        metadata = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
        dest = LIBRARY / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(
            skill_dir,
            dest,
            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
        )
        skills.append(
            {
                "id": name,
                "name": name,
                "title": first_heading(body) or name,
                "description": str(meta.get("description") or "").strip(),
                "keywords": meta.get("keywords") if isinstance(meta.get("keywords"), list) else [],
                "packageType": meta.get("packageType") or "instruction-skill",
                "instructionOnly": bool(meta.get("instructionOnly", True)),
                "version": str(metadata.get("version") or "1.0.0"),
                "href": f"library/{name}/SKILL.md",
            }
        )
    return skills


def main() -> None:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    for leftover in LIBRARY.iterdir():
        if leftover.is_dir():
            shutil.rmtree(leftover)
        else:
            leftover.unlink()

    skills = collect_skills()
    catalog = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "assets/skills",
        "count": len(skills),
        "skills": skills,
    }
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"synced {len(skills)} skill(s) from {SOURCE}")
    for skill in skills:
        print(f"  - {skill['id']} -> {skill['href']}")


if __name__ == "__main__":
    main()
