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
    """Build the compact label:value fact-sheet shown under the hero image.

    Row order and labels are locked by issue #11 (T11). Each row is hidden
    when its source value is empty. The `facts` block (top-level in the v2
    schema) holds season_months / lifespan_years / age_maturity; the other
    rows read from `taxonomy` / `habitat.water_types` / `physical` /
    `conservation.status`.
    """
    tax = meta.get("taxonomy", {})
    phys = meta.get("physical", {})
    hab = meta.get("habitat", {})
    facts = meta.get("facts", {}) or {}
    rows = []

    def add(label, value):
        if value:
            rows.append({"label": label, "value": value})

    add("Scientific name", (tax.get("scientific_name") or "").strip())
    add("Family", (tax.get("family") or "").strip())

    water = hab.get("water_types") or []
    if water:
        add("Water", ", ".join(w.title() for w in water))

    season = facts.get("season_months") or []
    if season:
        add("Season months", months_list(season))

    typ = phys.get("typical_length_cm")
    mx = phys.get("max_length_cm")
    if mx:
        add("Typical/max length", f"{typ} cm (max {mx})" if typ else f"max {mx} cm")
    elif typ:
        add("Typical/max length", f"{typ} cm")

    if phys.get("max_weight_kg"):
        add("Weight", f"{phys['max_weight_kg']} kg")

    if facts.get("lifespan_years"):
        add("Lifespan", f"{facts['lifespan_years']} years")

    if facts.get("age_maturity"):
        add("Age at maturity", f"{facts['age_maturity']}")

    status = meta.get("conservation", {}).get("status")
    if status:
        add("IUCN status", status)

    return rows


def build_distribution_blurb(meta):
    """Short prose caption for the Distribution block.

    v2 (per the redesign): the water-types half is gone (water types are
    in the fact-sheet now). The caption is just the geographic-scope hint
    derived from the lat/lon spread of the distribution points, plus the
    source string. Only emitted for species with ≥20 points so "local"
    species don't get a one-liner.
    """
    dist = meta.get("distribution", {})
    pts = dist.get("points") or []
    if len(pts) < 20:
        return None
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    if lat_range > 120 and lon_range > 120:
        scope = "Records span multiple continents."
    elif lat_range > 60 and lon_range > 60:
        scope = "Records span a broad geographic range."
    else:
        return None
    source = dist.get("source")
    if source:
        return f"{scope} Map shows {source.lower()}."
    return scope


def _behavior_markdown(behavior):
    """Render the v2 `behavior` frontmatter key as prose.

    In v2 the `behavior` key holds a free-text paragraph produced by
    `build_behavior_text()` in the importer (sentence-filtered FishBase
    `species.Comments`, see issue #12). The v1 structured shape
    (`{schooling, shoaling, solitary}`) is gone. Empty/None yields "".
    """
    if not behavior:
        return ""
    text = behavior.strip() if isinstance(behavior, str) else ""
    return text


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

    Returns a list of {key, title, html} in page order. v2 (per the redesign)
    keeps only three prose sections: Description, Biology, Behavior. The
    fact-sheet carries Size / Weight / Age / Lifespan / Age at maturity /
    Season months / IUCN status, so those are no longer prose sections.

    Description and Biology are pulled from the markdown body (when present)
    with the frontmatter as fallback; Behavior is a free-text string in
    `meta.behavior` produced by the importer's sentence filter.
    """
    sections = []

    def add(key, title, markdown):
        html = render_markdown(markdown) if markdown and markdown.strip() else ""
        if html and html.strip():
            sections.append({"key": key, "title": title, "html": html})

    add("description", "Description", body_sections.get("Description", meta.get("description", "")))
    add("biology", "Biology", body_sections.get("Biology", "") or "")

    behavior_text = _behavior_markdown(meta.get("behavior"))
    if behavior_text:
        add("behavior", "Behavior", behavior_text)

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
