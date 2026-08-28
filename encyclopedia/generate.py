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

# Make `encyclopedia` importable as a package for sibling modules
# (encyclopedia/ has no __init__.py, so prepend its parent).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from encyclopedia.import_species import months_list  # noqa: E402


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


def build_fact_sheet(meta):
    """Build the compact label:value fact-sheet shown under the hero image."""
    tax = meta.get("taxonomy", {})
    phys = meta.get("physical", {})
    hab = meta.get("habitat", {})
    rows = []

    def add(label, value):
        if value:
            rows.append({"label": label, "value": value})

    add("Scientific name", (tax.get("scientific_name") or "").strip())
    add("Family", (tax.get("family") or "").strip())

    water = hab.get("water_types") or []
    if water:
        add("Water", ", ".join(w.title() for w in water))

    typ = phys.get("typical_length_cm")
    mx = phys.get("max_length_cm")
    if mx:
        add("Typical/max length", f"{typ} cm (max {mx})" if typ else f"max {mx} cm")
    elif typ:
        add("Typical/max length", f"{typ} cm")

    if phys.get("max_weight_kg"):
        add("Weight", f"{phys['max_weight_kg']} kg")

    if phys.get("lifespan_years"):
        add("Lifespan", f"{phys['lifespan_years']} years")

    if hab.get("depth_range_m"):
        add("Depth range", f"{hab['depth_range_m']} m")

    status = meta.get("conservation", {}).get("status")
    if status:
        add("IUCN status", status)

    return rows


def build_distribution_blurb(meta):
    """Short prose blurb for the Distribution block.

    Combines the water types and a quick geographic scope from the available
    distribution points (so a wide-spread species reads as "across the Northern
    Hemisphere", not just "inhabits saltwater waters").
    """
    hab = meta.get("habitat", {})
    tax = meta.get("taxonomy", {})
    dist = meta.get("distribution", {})
    common = (tax.get("common_name") or "").strip() or "This species"
    water = hab.get("water_types") or []
    parts = []
    if water:
        parts.append(f"{common} inhabits {', '.join(w.title() for w in water)} waters.")
    pts = dist.get("points") or []
    if len(pts) >= 20:
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        if lat_range > 120 and lon_range > 120:
            parts.append("Records span multiple continents.")
        elif lat_range > 60 and lon_range > 60:
            parts.append("Records span a broad geographic range.")
    if dist.get("source"):
        parts.append(f"Map shows {dist['source'].lower()}.")
    return " ".join(parts).strip() if parts else None


def _behavior_markdown(behavior):
    """Render the `behavior` frontmatter block as a short prose paragraph.

    Empty/None behavior yields "" so the section is dropped from the page.
    """
    if not behavior:
        return ""
    parts = []

    def qual(freq, lifestage):
        bits = []
        if freq:
            bits.append(str(freq))
        if lifestage:
            bits.append(f"as {lifestage}")
        return f" ({', '.join(bits)})" if bits else ""

    if behavior.get("schooling"):
        parts.append(f"Forms schools{qual(behavior.get('schooling_frequency'), behavior.get('schooling_lifestage'))}.")
    if behavior.get("shoaling"):
        parts.append(f"Forms loose shoals{qual(behavior.get('shoaling_frequency'), behavior.get('shoaling_lifestage'))}.")
    if behavior.get("solitary"):
        parts.append("Often solitary")

    return "\n\n".join(parts)


def split_markdown_sections(md_body):
    """Split markdown into {heading: [lines]} by `## ` headings.

    Content before the first heading is discarded (used to carry the lead in
    older files). Returns an ordered dict heading -> html string.
    """
    sections = {}
    current = None
    buffer = []
    for raw in md_body.splitlines():
        if raw.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = raw[3:].strip()
            buffer = []
        else:
            buffer.append(raw)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def build_prose_sections(meta, body_sections):
    """Build the fixed-order prose sections, dropping any that are empty.

    Returns a list of {key, title, html} in page order. Description and Biology
    come from the markdown body; Size/Weight/Age/Seasonality/Conservation are
    rendered from frontmatter.
    """
    phys = meta.get("physical", {})
    bio = meta.get("biology", {})
    angling = meta.get("angling", {})

    sections = []

    def add(key, title, markdown):
        html = render_markdown(markdown) if markdown and markdown.strip() else ""
        if html and html.strip():
            sections.append({"key": key, "title": title, "html": html})

    add("description", "Description", body_sections.get("Description", meta.get("description", "")))

    size = []
    typ = phys.get("typical_length_cm")
    mx = phys.get("max_length_cm")
    if typ and mx:
        size.append(f"Typical length is {typ} cm, with a maximum recorded length of {mx} cm.")
    elif mx:
        size.append(f"Maximum recorded length is {mx} cm.")
    elif typ:
        size.append(f"Typical length is {typ} cm.")
    add("size", "Size", "\n\n".join(size))

    weight = []
    if phys.get("max_weight_kg"):
        weight.append(f"Maximum recorded weight is {phys['max_weight_kg']} kg.")
    add("weight", "Weight", "\n\n".join(weight))

    age = []
    if phys.get("lifespan_years"):
        age.append(f"Lifespan is around {phys['lifespan_years']} years.")
    if bio.get("age_maturity"):
        age.append(f"Sexual maturity is reached at about {bio['age_maturity']} of age.")
    add("age", "Age", "\n\n".join(age))

    add("biology", "Biology", body_sections.get("Biology", "") or "")

    behavior_md = _behavior_markdown(meta.get("behavior") or {})
    if behavior_md:
        add("behavior", "Behavior", behavior_md)

    months = angling.get("season_months") or []
    if months:
        add("seasonality", "Seasonality",
            f"Its most productive fishing months in the Northern Hemisphere are typically {months_list(months)}, though exact timing depends on local climate and water temperature.")
    elif angling.get("best_months"):
        add("seasonality", "Seasonality", f"Best fishing months: {angling['best_months']}.")

    status = meta.get("conservation", {}).get("status")
    if status:
        add("conservation", "Conservation", f"IUCN conservation status: **{status}**.")

    return sections


def get_distribution_for_template(meta):
    """Extract distribution data for the Leaflet map.

    Prefers real occurrence points (FishBase) as a density scatter; falls back
    to named regions when no points are available.
    """
    dist = meta.get("distribution", {})
    points = dist.get("points", [])
    regions = []
    for r in dist.get("regions", []):
        regions.append({
            "name": r["name"],
            "description": r.get("description", ""),
            "coordinates": [{"lat": c.get("lat"), "lng": c.get("lng"),
                             "label": c.get("label", "")} for c in r.get("coordinates", [])]
        })
    result = {"points": points, "regions": regions, "source": dist.get("source")}
    if not points and not regions:
        return None
    return result


def build_html(meta, body_md, source_file):
    """Render the complete HTML page from metadata and body."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("base.html")

    tax = meta.get("taxonomy", {})
    title = tax.get("common_name") or meta.get("id", "").replace("-", " ").title()
    scientific = tax.get("scientific_name")
    body_sections = split_markdown_sections(body_md)

    context = {
        "title": title,
        "scientific_name": scientific,
        "image": meta.get("image"),
        "fact_sheet": build_fact_sheet(meta),
        "distribution": get_distribution_for_template(meta),
        "distribution_blurb": build_distribution_blurb(meta),
        "prose_sections": build_prose_sections(meta, body_sections),
        "source_file": source_file,
        "source_path": f"encyclopedia/data/{source_file}",
    }

    return template.render(**context)


def process_file(md_path):
    """Process a single markdown file into HTML."""
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    slug = meta.get("slug", md_path.stem)
    rel_path = md_path.relative_to(DATA_DIR)
    source_file = str(rel_path)

    html = build_html(meta, body, source_file)

    out_file = OUT_DIR / f"{slug}.html"
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for md_file in find_md_files(DATA_DIR, specific):
        try:
            process_file(md_file)
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
        water = meta.get("habitat", {}).get("water_types", [None])[0] if meta.get("habitat", {}).get("water_types") else None
        slug = md_file.stem
        species_list.append({
            "common_name": tax.get("common_name", slug.replace("-", " ").title()),
            "scientific_name": tax.get("scientific_name", ""),
            "water_type": water.title() if water else None,
            "path": f"{slug}.html",
        })

    html = template.render(species_list=species_list)
    out_file = OUT_DIR / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  ✓ index.html ({len(species_list)} species)")
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
