#!/usr/bin/env python3
"""
Fishing Encyclopedia Generator
Converts Markdown + YAML frontmatter files into HTML pages with interactive maps.

Usage:
    python3 generate.py                    # Build all
    python3 generate.py fish/zander        # Build one
    python3 generate.py --watch            # Watch mode (rebuild on change)
"""

import sys
import os
import json
import yaml
import time
from pathlib import Path
from markdown_it import MarkdownIt

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "encyclopedia" / "data"
OUT_DIR = ROOT / "encyclopedia" / "out"
TEMPLATE_DIR = ROOT / "encyclopedia" / "templates"


def parse_frontmatter(text):
    """Parse YAML frontmatter and markdown body from a file."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return meta, body
    return {}, text


def render_markdown(md_text):
    """Convert markdown to HTML."""
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    return md.render(md_text)


def build_info_cards(meta):
    """Extract key stats into display cards for the template."""
    cards = []
    phys = meta.get("physical", {})
    if phys.get("typical_length_cm"):
        cards.append({
            "label": "Size",
            "value": f"{phys['typical_length_cm']} cm",
            "detail": f"Max: {phys.get('max_length_cm', '?')} cm"
        })
    if phys.get("typical_weight_kg"):
        cards.append({
            "label": "Weight",
            "value": f"{phys['typical_weight_kg']} kg",
            "detail": f"Max: {phys.get('max_weight_kg', '?')} kg"
        })
    if phys.get("lifespan_years"):
        cards.append({
            "label": "Lifespan",
            "value": f"{phys['lifespan_years']} years",
            "detail": None
        })

    hab = meta.get("habitat", {})
    if hab.get("water_types"):
        cards.append({
            "label": "Water Types",
            "value": ", ".join(hab["water_types"]).title(),
            "detail": f"Depth: {hab.get('depth_range_m', '?')} m"
        })

    temp = hab.get("water_temperature", {})
    if temp.get("optimal_celsius"):
        cards.append({
            "label": "Water Temp",
            "value": f"{temp['optimal_celsius']}°C",
            "detail": f"Range: {temp.get('range_celsius', '?')}°C"
        })

    behav = meta.get("behavior", {})
    if behav.get("feeding", {}).get("type"):
        cards.append({
            "label": "Diet",
            "value": behav["feeding"]["type"],
            "detail": ", ".join(behav["feeding"].get("peak_feeding_times", []))
        })

    fish = meta.get("fishing", {})
    if fish.get("difficulty"):
        cards.append({
            "label": "Difficulty",
            "value": fish["difficulty"],
            "detail": None
        })

    return cards


def get_distribution_for_template(meta):
    """Extract distribution regions for the Leaflet map."""
    dist = meta.get("distribution", {})
    regions = dist.get("regions", [])
    result = []
    for r in regions:
        result.append({
            "name": r["name"],
            "description": r.get("description", ""),
            "coordinates": r.get("coordinates", [])
        })
    return result


def build_html(meta, body_html, source_file):
    """Render the complete HTML page from metadata and body."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("base.html")

    title = meta.get("id", "").replace("-", " ").title()
    if meta.get("scientific_name"):
        title = meta["id"].replace("-", " ").title()

    breadcrumb = None
    cat = meta.get("category", "")
    if cat:
        breadcrumb = cat.replace("-", " ").title()

    context = {
        "title": title,
        "scientific_name": meta.get("scientific_name"),
        "category": cat,
        "breadcrumb_category": breadcrumb,
        "image": meta.get("image"),
        "info_cards": build_info_cards(meta),
        "distribution": get_distribution_for_template(meta),
        "body_html": body_html,
        "source_file": source_file,
        "source_path": f"../../../encyclopedia/data/{source_file}",
    }

    return template.render(**context)


def process_file(md_path, out_dir):
    """Process a single markdown file into HTML."""
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    body_html = render_markdown(body)

    slug = meta.get("slug", md_path.stem)
    rel_path = md_path.relative_to(DATA_DIR)
    source_file = str(rel_path)

    html = build_html(meta, body_html, source_file)

    out_file = out_dir / f"{slug}.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    print(f"  ✓ {rel_path} → {out_file.relative_to(ROOT)}")
    return out_file


def build_all(specific=None):
    """Build all or specific encyclopedia entries."""
    print("Fishing Encyclopedia — Building...\n")
    count = 0

    for category_dir in sorted(DATA_DIR.iterdir()):
        if not category_dir.is_dir():
            continue

        out_category = OUT_DIR / category_dir.name
        out_category.mkdir(parents=True, exist_ok=True)

        for md_file in sorted(category_dir.glob("*.md")):
            if specific and specific not in str(md_file.relative_to(DATA_DIR)):
                continue
            try:
                process_file(md_file, out_category)
                count += 1
            except Exception as e:
                print(f"  ✗ {md_file.name}: {e}")

    print(f"\nDone — {count} pages generated in {OUT_DIR.relative_to(ROOT)}/")


def watch_mode():
    """Watch for changes and rebuild."""
    print("Watching for changes... (Ctrl+C to stop)\n")
    seen = {}
    while True:
        for md_file in DATA_DIR.rglob("*.md"):
            mtime = md_file.stat().st_mtime
            if md_file not in seen or seen[md_file] != mtime:
                seen[md_file] = mtime
                try:
                    process_file(md_file, OUT_DIR / md_file.parent.name)
                except Exception as e:
                    print(f"  ✗ {md_file.name}: {e}")
        time.sleep(1)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_mode()
    elif len(sys.argv) > 1 and sys.argv[1] != "--watch":
        build_all(sys.argv[1])
    else:
        build_all()
