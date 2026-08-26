#!/usr/bin/env python3
"""
Fishing Encyclopedia Generator
Converts Markdown + YAML frontmatter files into HTML pages with interactive maps.

Usage:
    python3 generate.py                    # Build all
    python3 generate.py fish/percidae/sander/zander  # Build one
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

    temp = hab.get("temperature", {})
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
            "detail": ", ".join(behav["feeding"].get("peak_times", []))
        })

    angling = meta.get("angling", {})
    if angling.get("difficulty"):
        cards.append({
            "label": "Difficulty",
            "value": angling["difficulty"],
            "detail": None
        })
    if angling.get("fight_rating"):
        cards.append({
            "label": "Fight Rating",
            "value": f"{angling['fight_rating']}/10",
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


def get_taxonomy_breadcrumb(meta):
    """Build taxonomy breadcrumb from taxonomy fields."""
    tax = meta.get("taxonomy", {})
    parts = []
    for key in ["class", "order", "family", "genus"]:
        if tax.get(key):
            parts.append(tax[key])
    return " > ".join(parts) if parts else None


def build_html(meta, body_html, source_file):
    """Render the complete HTML page from metadata and body."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("base.html")

    tax = meta.get("taxonomy", {})
    title = tax.get("common_name") or meta.get("id", "").replace("-", " ").title()
    scientific = tax.get("scientific_name")

    context = {
        "title": title,
        "scientific_name": scientific,
        "category": tax.get("family", ""),
        "breadcrumb_category": tax.get("family", "").title(),
        "taxonomy_breadcrumb": get_taxonomy_breadcrumb(meta),
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

    # Preserve taxonomy path: fish/family/genus/species.html
    out_file = out_dir / f"{slug}.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    print(f"  ✓ {rel_path} → {out_file.relative_to(ROOT)}")
    return out_file


def find_md_files(data_dir, specific=None):
    """Find all markdown files in the data directory, supporting taxonomy paths."""
    files = []
    for md_file in sorted(data_dir.rglob("*.md")):
        # Skip schema and non-species files
        if md_file.name.startswith("_") or md_file.name == "fish-profile-schema.yaml":
            continue
        if specific and specific not in str(md_file.relative_to(data_dir)):
            continue
        files.append(md_file)
    return files


def build_all(specific=None):
    """Build all or specific encyclopedia entries."""
    print("Fishing Encyclopedia — Building...\n")
    count = 0

    for category_dir in sorted(DATA_DIR.iterdir()):
        if not category_dir.is_dir():
            continue

        out_category = OUT_DIR / category_dir.name
        out_category.mkdir(parents=True, exist_ok=True)

        for md_file in find_md_files(category_dir, specific):
            try:
                process_file(md_file, out_category)
                count += 1
            except Exception as e:
                print(f"  ✗ {md_file.name}: {e}")

    print(f"\nDone — {count} pages generated in {OUT_DIR.relative_to(ROOT)}/")

    build_index()


def build_index():
    """Build the index page listing all species, techniques, and gear."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("index.html")

    species_list = []
    for md_file in sorted(DATA_DIR.rglob("fish/*/*/*.md")):
        if md_file.name.startswith("_"):
            continue
        text = md_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        tax = meta.get("taxonomy", {})
        rel = md_file.relative_to(DATA_DIR / "fish")
        slug = md_file.stem
        # URL: /fish/{family}/{genus}/{species}.html
        parts = list(rel.parent.parts) + [f"{slug}.html"]
        species_list.append({
            "common_name": tax.get("common_name", slug.replace("-", " ").title()),
            "scientific_name": tax.get("scientific_name", ""),
            "path": "/fish/" + "/".join(parts),
        })

    techniques = []
    for md_file in sorted((DATA_DIR / "techniques").glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        techniques.append({
            "name": meta.get("name", md_file.stem.replace("-", " ").title()),
            "path": f"/techniques/{md_file.stem}.html",
        })

    gear = []
    for md_file in sorted((DATA_DIR / "gear").glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        gear.append({
            "name": meta.get("name", md_file.stem.replace("-", " ").title()),
            "path": f"/gear/{md_file.stem}.html",
        })

    html = template.render(species_list=species_list, techniques=techniques, gear=gear)
    out_file = OUT_DIR / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  ✓ index.html ({len(species_list)} species, {len(techniques)} techniques, {len(gear)} gear)")
    return out_file


def watch_mode():
    """Watch for changes and rebuild."""
    print("Watching for changes... (Ctrl+C to stop)\n")
    seen = {}
    while True:
        for md_file in DATA_DIR.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            mtime = md_file.stat().st_mtime
            if md_file not in seen or seen[md_file] != mtime:
                seen[md_file] = mtime
                try:
                    rel = md_file.relative_to(DATA_DIR)
                    out_dir = OUT_DIR / rel.parent
                    process_file(md_file, out_dir)
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
