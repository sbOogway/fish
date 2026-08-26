#!/usr/bin/env python3
"""Validate fish profile markdown files against the schema."""
import sys
import yaml
from pathlib import Path

DATA_DIR = Path("encyclopedia/data/fish")
REQUIRED_FIELDS = ["id", "taxonomy.common_name", "taxonomy.scientific_name", "taxonomy.family"]


def get_nested(meta, dotpath):
    parts = dotpath.split(".")
    val = meta
    for p in parts:
        if not isinstance(val, dict):
            return None
        val = val.get(p)
    return val


def validate_file(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return [f"{path}: missing frontmatter"]
    parts = text.split("---", 2)
    if len(parts) < 3:
        return [f"{path}: malformed frontmatter"]
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        return [f"{path}: frontmatter is not a dict"]
    errors = []
    for field in REQUIRED_FIELDS:
        if not get_nested(meta, field):
            errors.append(f"{path}: missing required field '{field}'")
    tax = meta.get("taxonomy", {})
    if tax.get("family") and tax.get("genus") and tax.get("species"):
        expected_dir = DATA_DIR / tax["family"].lower() / tax["genus"].lower()
        if expected_dir not in path.parents:
            errors.append(f"{path}: expected path {expected_dir}/...")
    return errors


def main():
    all_errors = []
    for md_file in sorted(DATA_DIR.rglob("*.md")):
        all_errors.extend(validate_file(md_file))
    if all_errors:
        for e in all_errors:
            print(f"  ✗ {e}", file=sys.stderr)
        sys.exit(1)
    count = len(list(DATA_DIR.rglob("*.md")))
    print(f"  ✓ {count} fish profiles valid")


if __name__ == "__main__":
    main()
