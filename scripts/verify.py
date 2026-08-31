#!/usr/bin/env python3
"""Verify the TreeSeed skill and its immutable catalog evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path


DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def fail(message: str) -> None:
    raise ValueError(message)


def verify(root: Path, check_remote: bool = False) -> None:
    skill = root / "SKILL.md"
    receipt_path = root / "catalog-receipt.json"
    if not skill.is_file() or not receipt_path.is_file():
        fail("SKILL.md and catalog-receipt.json are required")

    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\nname: treeseed\n" not in text:
        fail("SKILL.md must declare the treeseed frontmatter name")
    for target in LINK.findall(text):
        if "://" not in target and not (root / target).is_file():
            fail(f"broken local link: {target}")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schemaVersion") != "treeseed.skill-catalog-receipt/v2":
        fail("unsupported or stale catalog receipt schema")
    if receipt.get("skillsCliVersion") != "1.5.23":
        fail("unexpected Vercel Labs Skills CLI version")

    for owner in ("sdk", "api"):
        source_commit = receipt.get(owner, {}).get("sourceCommit", "")
        if not COMMIT.fullmatch(source_commit):
            fail(f"{owner}.sourceCommit must be an exact commit")

    for owner, artifact_name in (("sdk", "contractBundle"), ("api", "componentManifest")):
        artifact = receipt[owner][artifact_name]
        if not DIGEST.fullmatch(artifact.get("digest", "")):
            fail(f"{owner}.{artifact_name}.digest is invalid")
        if check_remote:
            with urllib.request.urlopen(artifact["url"], timeout=30) as response:
                actual = "sha256:" + hashlib.sha256(response.read()).hexdigest()
            if actual != artifact["digest"]:
                fail(f"{owner}.{artifact_name} digest mismatch")

    forbidden_home_prefix = "/" + "home/"
    for path in root.rglob("*"):
        if path.is_file() and not {".git", "__pycache__"}.intersection(path.parts):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if forbidden_home_prefix in content:
                fail(f"personal home path in {path.relative_to(root)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--check-remote", action="store_true")
    args = parser.parse_args()
    try:
        verify(Path(args.root).resolve(), args.check_remote)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"skill verification failed: {error}", file=sys.stderr)
        return 1
    print("TreeSeed skill verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
