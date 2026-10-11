#!/usr/bin/env python3
"""Scan files for private information that must not appear in public skills.

Checks: IP addresses, Windows drive-letter paths, Unix home/root paths,
email addresses, credential/token string prefixes, credential file names.
Git metadata (.git/) is skipped: reflogs carry committer identities.
Rules are generic patterns only; no real private values are embedded here.
Host names and person names cannot be matched generically - they are
covered by the drafting workflow (drafting agents never see private
material) and by human review before publishing.

Usage:
    python check_private.py [PATH] [--exclude NAME]...

PATH defaults to the repository root (parent of this script's directory).
Exit codes: 0 = clean, 1 = findings, 2 = usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".zip", ".gz",
    ".7z", ".vsix", ".pdf", ".exe", ".dll", ".so", ".a", ".bin", ".elf",
    ".hex", ".woff", ".woff2", ".ttf", ".mp3", ".mp4",
}

MAX_FILE_BYTES = 20 * 1024 * 1024

# (rule name, pattern, whitelist function: match string -> bool)
def _ip_whitelist(match: str) -> bool:
    if match in {"0.0.0.0", "127.0.0.1", "255.255.255.255"}:
        return True
    octets = match.split(".")
    if any(not o.isdigit() or int(o) > 255 for o in octets):
        return True  # not a valid IPv4 (e.g. a version string like 10.0.26200)
    return False


def _email_whitelist(match: str) -> bool:
    domain = match.split("@", 1)[1].lower()
    return domain.startswith(("example.com", "example.org", "example.net"))


RULES = [
    ("ipv4-address",
     re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
     _ip_whitelist),
    ("windows-drive-path",
     re.compile(r"\b[A-Za-z]:[\\\\/]"),
     None),
    ("unix-home-path",
     re.compile(r"(?<![\w.])/(?:home/[A-Za-z0-9_.\-]+|root(?:/|\b)|Users/[A-Za-z0-9_.\-]+)"),
     None),
    ("email-address",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+\b"),
     _email_whitelist),
    ("github-token",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b|\bgithub_pat_[A-Za-z0-9_]{16,}\b"),
     None),
    ("api-key-prefix",
     re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b|\bxox[abprs]-[A-Za-z0-9-]{10,}\b|\bAKIA[0-9A-Z]{16}\b"),
     None),
    ("credential-filename",
     re.compile(r"\b(?:auth\.json|credentials?\.json|id_rsa(?:\.pub)?|\.netrc)\b"),
     None),
]


def iter_files(root: Path, excludes: list[str]):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue  # git metadata, not repo content
        if path.resolve() == Path(__file__).resolve():
            continue  # the rule list itself contains generic pattern text
        rel = path.relative_to(root).as_posix()
        if any(part in excludes for part in path.parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                print(f"SKIP (too large): {rel}", file=sys.stderr)
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"SKIP (unreadable: {exc}): {rel}", file=sys.stderr)
            continue
        yield rel, text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", type=Path, default=None,
                        help="directory to scan (default: repo root)")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="NAME",
                        help="skip files whose path contains NAME (repeatable)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = args.path.resolve() if args.path else script_dir.parent
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    findings = 0
    for rel, text in iter_files(root, args.exclude):
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern, whitelist in RULES:
                for match in pattern.finditer(line):
                    token = match.group(0)
                    if whitelist and whitelist(token):
                        continue
                    findings += 1
                    shown = token if len(token) <= 60 else token[:57] + "..."
                    print(f"{rel}:{lineno}: [{name}] {shown}")

    if findings:
        print(f"\nFAILED: {findings} finding(s). Review each match above.")
        return 1
    print("OK: no private-information patterns found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
