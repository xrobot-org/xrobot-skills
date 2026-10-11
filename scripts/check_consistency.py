#!/usr/bin/env python3
"""Check version consistency across the repository metadata files.

Checks:
- .claude-plugin/marketplace.json: metadata.version exists and is a
  version of the form X.Y.Z.
- CHANGELOG.md: the first "## <version>" release heading, skipping any
  "## Unreleased" heading, matches marketplace.json.
- skills/xrobot/SKILL.md and skills/xrobot-contrib/SKILL.md: the YAML
  frontmatter (between the first "---" line and the next "---" line)
  has non-empty name and description fields, and a version field equal
  to marketplace.json.

Usage:
    python check_consistency.py [PATH]

PATH defaults to the repository root (parent of this script's directory).
Exit codes: 0 = consistent, 1 = findings, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
HEADING_PATTERN = re.compile(r"^##\s+(\S+)")

MARKETPLACE_RELPATH = ".claude-plugin/marketplace.json"
CHANGELOG_RELPATH = "CHANGELOG.md"
SKILL_RELPATHS = [
    "skills/xrobot/SKILL.md",
    "skills/xrobot-contrib/SKILL.md",
]


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Return the simple 'key: value' fields of a leading '---' block.

    Returns None when the text does not start with '---' or the block
    is never closed. Values are single-line strings; surrounding quotes
    are stripped and colons inside a value are kept.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    return None  # the frontmatter block is never closed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", type=Path, default=None,
                        help="repository root to check (default: parent of this script's directory)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = args.path.resolve() if args.path else script_dir.parent
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    findings: list[str] = []

    def add(rel: str, detail: str) -> None:
        findings.append(f"{rel}: {detail}")

    marketplace_version: str | None = None
    try:
        data = json.loads((root / MARKETPLACE_RELPATH).read_text(encoding="utf-8"))
    except FileNotFoundError:
        add(MARKETPLACE_RELPATH, "file not found")
    except (OSError, ValueError) as exc:
        add(MARKETPLACE_RELPATH, f"cannot read JSON ({exc})")
    else:
        metadata = data.get("metadata") if isinstance(data, dict) else None
        version = metadata.get("version") if isinstance(metadata, dict) else None
        if isinstance(version, str) and SEMVER_PATTERN.match(version):
            marketplace_version = version
        else:
            add(MARKETPLACE_RELPATH,
                f"metadata.version {version!r} is missing or not in X.Y.Z form")

    try:
        changelog = (root / CHANGELOG_RELPATH).read_text(encoding="utf-8")
    except OSError:
        add(CHANGELOG_RELPATH, "file not found")
    else:
        release_version = None
        for line in changelog.splitlines():
            match = HEADING_PATTERN.match(line)
            if not match:
                continue
            token = match.group(1)
            if token.lower() == "unreleased":
                continue
            if not SEMVER_PATTERN.match(token):
                continue
            release_version = token
            break
        if release_version is None:
            add(CHANGELOG_RELPATH,
                "no '## <version>' release heading found after '## Unreleased'")
        elif (marketplace_version is not None
              and release_version != marketplace_version):
            add(CHANGELOG_RELPATH,
                f"first release heading {release_version} does not match "
                f"marketplace.json version {marketplace_version}")

    for rel in SKILL_RELPATHS:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            add(rel, "file not found")
            continue
        fields = read_frontmatter(text)
        if fields is None:
            add(rel, "YAML frontmatter between the first two '---' lines is missing")
            continue
        for key in ("name", "description"):
            if not fields.get(key):
                add(rel, f"frontmatter '{key}' is missing or empty")
        version = fields.get("version")
        if not version:
            add(rel, "frontmatter 'version' is missing")
        elif not SEMVER_PATTERN.match(version):
            add(rel, f"frontmatter version {version!r} is not in X.Y.Z form")
        elif (marketplace_version is not None
              and version != marketplace_version):
            add(rel,
                f"frontmatter version {version} does not match "
                f"marketplace.json version {marketplace_version}")

    if findings:
        for line in findings:
            print(line)
        print(f"\nFAILED: {len(findings)} finding(s). Align the versions above.")
        return 1
    print("OK: marketplace.json, CHANGELOG.md and both SKILL.md frontmatter "
          "versions are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
