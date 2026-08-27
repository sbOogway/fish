#!/usr/bin/env python3
"""
Import species from the FishRadar catalog, enriched with Wikipedia/Wikidata,
generating one profile .md file per species under encyclopedia/data/fish/.

Sources combined (see docs/adr/0002-species-data-pipeline.md):
  - FishRadar data/species.json     -> species list, aliases, environment,
                                       latRange, seasonMonths, conservation
  - Wikipedia REST page/summary     -> page title, lead extract, hero image,
                                       wikibase_item
  - Wikidata SPARQL (P171/P105)     -> class, order, family, genus

Idempotent: species that already have a profile (matched by scientific name)
are skipped, so hand-crafted profiles are never clobbered. A small JSON cache
avoids re-hitting the external APIs on rerun.
"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "encyclopedia" / "data"
FISH_DIR = DATA_DIR / "fish"
OUT_DIR = ROOT / "encyclopedia" / "out"
CACHE = OUT_DIR / ".import-cache.json"

USER_AGENT = "FishpediaImporter/1.0 (fishing encyclopedia builder; contact: mattia@example.com)"

FISHRADAR_URL = ("https://raw.githubusercontent.com/linkanlabs-ctrl/"
                 "fishing-species-catalog/main/data/species.json")

RANK_FILTER = {
    "Q37517": "order",
    "Q35409": "family",
    "Q34740": "genus",
    "Q37528": "class",
}

CONSERVATION = {
    "cites-ii": "CITES-II",
    "no-retention": "NO-RETENTION",
    "permit-required": "PERMIT-REQUIRED",
    "vulnerable": "VU",
}

# Family fallback for species whose Wikidata family rank doesn't resolve
# (keyed by scientific name). Keeps taxonomy out of "Incertae sedis".
FAMILY_OVERRIDES = {
    "tinca tinca": "Tincidae",
    "colossoma macropomum": "Serrasalmidae",
    "gerres cinereus": "Gerreidae",
    "cyprinus rubrofuscus": "Cyprinidae",
    "isurus oxyrinchus": "Lamnidae",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def http_json(url, accept="application/json", timeout=45):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def wikipedia_summary(scientific):
    q = urllib.parse.quote(scientific.replace(" ", "_"))
    try:
        return http_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}")
    except Exception:
        return None


def wikibase_item_from_title(title):
    t = urllib.parse.quote(title.replace(" ", "_"))
    url = ("https://en.wikipedia.org/w/api.php?action=query&titles=" + t +
           "&prop=pageprops&ppprop=wikibase_item&format=json&formatversion=2&redirects=1")
    try:
        d = http_json(url)
        pages = d.get("query", {}).get("pages", [])
        if pages and "pageprops" in pages[0]:
            return pages[0]["pageprops"].get("wikibase_item")
    except Exception:
        pass
    return None


def wikidata_taxonomy(qid):
    query = f"""SELECT ?rank ?itemLabel WHERE {{
  wd:{qid} wdt:P171* ?ancestor .
  ?ancestor p:P105/ps:P105 ?rank .
  ?ancestor rdfs:label ?itemLabel FILTER(LANG(?itemLabel)='en')
  FILTER(?rank IN (wd:Q37517, wd:Q35409, wd:Q34740, wd:Q37528))
}}"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query})
    try:
        d = http_json(url, accept="application/sparql-results+json", timeout=60)
    except Exception:
        return {}
    out = {}
    for b in d.get("results", {}).get("bindings", []):
        rank = b["rank"].get("value", "").split("/")[-1]
        role = RANK_FILTER.get(rank)
        name = b.get("itemLabel", {}).get("value")
        if role and name:
            out[role] = name
    return out


def load_fishradar():
    return http_json(FISHRADAR_URL, timeout=60)


def read_existing():
    """Map scientific name -> profile path for species already in data/fish."""
    existing = {}
    for md in FISH_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except Exception:
            continue
        sci = (meta.get("taxonomy") or {}).get("scientific_name")
        if sci:
            existing[sci.lower()] = md
    return existing


def distribution_from_latrange(english, lat):
    """Build a distribution.regions list from a latitude band."""
    if not lat or len(lat) != 2:
        return []
    lo, hi = sorted(lat)
    regions = [
        {
            "name": "Northern range",
            "description": "Northern extent of the species' range",
            "coordinates": [{"lat": hi, "lng": 0, "label": "Northern limit"}],
        },
        {
            "name": "Southern range",
            "description": "Southern extent of the species' range",
            "coordinates": [{"lat": lo, "lng": 0, "label": "Southern limit"}],
        },
    ]
    if lo <= 0 <= hi:
        regions.append({
            "name": "Equatorial range",
            "description": "Tropical extent of the species' range",
            "coordinates": [{"lat": 0, "lng": 0, "label": "Equator"}],
        })
    return regions


def build_profile(species, summary, tax):
    sci = species["scientific"].strip()
    common = (species["english"] or "").strip()
    slug = species["id"] or layout_slug(sci)

    if " " in sci:
        genus, species_epithet = sci.split(" ", 1)
    else:
        genus, species_epithet = sci, ""

    water = species["environment"]
    water_types = ["saltwater"] if water == "saltwater" else ["freshwater"]
    season = species.get("seasonMonths") or []

    family = FAMILY_OVERRIDES.get(sci.lower()) or tax.get("family") or "Incertae sedis"
    # Non-fish (cephalopod) families in the catalog: correct the class.
    CEPHALOPOD_FAMILIES = {"Octopodidae", "Sepiidae", "Loliginidae", "Sepiolidae"}
    fish_class = "Cephalopoda" if family in CEPHALOPOD_FAMILIES else (tax.get("class") or "Actinopterygii")
    conservation = CONSERVATION.get(species.get("conservationStatus"), "LC")

    meta = {
        "id": slug,
        "slug": slug,
        "taxonomy": {
            "class": fish_class,
            "order": tax.get("order") or "",
            "family": family,
            "genus": genus,
            "species": species_epithet,
            "scientific_name": sci,
            "common_name": common,
            "aliases": species.get("aliases") or [],
        },
        "sources": {
            "fishradar_id": slug,
            "wikidata_id": summary.get("wikibase_item") if summary else None,
        },
        "habitat": {
            "water_types": water_types,
            "_comment": "TODO: enrich from FishBase (depth, substrate, temperature)",
        },
        "angling": {
            "best_months": months_list(season),
            "season_months": season,
            "_comment": "TODO: enrich from FishBase/FishFYI (bait, techniques, difficulty)",
        },
        "distribution": {
            "native": True,
            "regions": distribution_from_latrange(common, species.get("latRange")),
        },
        "conservation": {"status": conservation},
    }

    body = build_body(common, sci, water, season, (summary or {}).get("extract"))

    if summary and summary.get("originalimage"):
        image_url = summary["originalimage"]["source"].split("?")[0]
        page = (summary.get("content_urls") or {}).get("desktop", {}).get("page")
        meta["image"] = {
            "url": image_url,
            "alt": f"{common} ({sci})",
            "credit": f"Wikipedia — {summary.get('title', '')}",
            "credit_url": page,
        }

    frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100)
    text = "---\n" + frontmatter + "---\n\n" + body.strip() + "\n"
    text += "\n<!-- generated by import_species.py from FishRadar + Wikipedia/Wikidata; enrich fields marked TODO -->\n"
    return text


def months_list(months):
    names = ", ".join(MONTH_NAMES[m - 1] for m in sorted(months) if 1 <= m <= 12)
    return names or "year-round"


def build_body(common, sci, water, season, extract):
    water_label = "saltwater (sea and brackish water)" if water == "saltwater" else "freshwater"
    season_text = months_list(season)
    lines = []
    if extract:
        lines.append(extract.strip())
        lines.append("")
    lines.append("## Habitat")
    lines.append(f"{common} is a {water_label} species. It is targeted across much of its range, with fishing conditions varying by season and locality.")
    lines.append("")
    lines.append("## Seasonality")
    lines.append(f"Its most productive fishing months in the Northern Hemisphere are typically {season_text}, though exact timing depends on local climate and water temperature.")
    lines.append("")
    lines.append("## Conservation")
    lines.append("Always observe local regulations. Handle fish carefully, use appropriate tackle, and promptly release protected or out-of-season specimens.")
    lines.append("")
    return "\n".join(lines)


def layout_slug(scientific):
    return scientific.replace(" ", "-").lower()


def main():
    FISH_DIR.mkdir(parents=True, exist_ok=True)

    species_list = load_fishradar()
    existing = read_existing()
    print(f"FishRadar catalog: {len(species_list)} species; existing profiles: {len(existing)}\n")

    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    written = skipped = 0
    for sp in species_list:
        sci = (sp.get("scientific") or "").strip()
        if not sci:
            skipped += 1
            continue
        key = sci.lower()
        if key in existing:
            print(f"  - skip (hand-crafted): {sci}")
            skipped += 1
            continue

        info = cache.get(key, {})
        if not info:
            summary = wikipedia_summary(sci)
            qid = wikibase_item_from_title(summary.get("title", "")) if summary else None
            tax = wikidata_taxonomy(qid) if qid else {}
            info = {"summary": summary, "qid": qid, "tax": tax}
            cache[key] = info
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            time.sleep(0.35)

        if not info["summary"]:
            print(f"  ✗ no wikipedia page: {sci}")
            skipped += 1
            continue

        # Directory (family/genus) must match the frontmatter exactly:
        # genus from the scientific name's first word, family from Wikidata,
        # both kebab-cased for the filesystem (validator computes the same way).
        fam_override = FAMILY_OVERRIDES.get(key)
        family = (fam_override or info["tax"].get("family") or "incertae sedis").lower().replace(" ", "-")
        genus = (sci.split(" ")[0] if " " in sci else "unknown").lower().replace(" ", "-")
        gen_dir = FISH_DIR / family / genus
        gen_dir.mkdir(parents=True, exist_ok=True)
        slug = sp.get("id") or layout_slug(sci)
        out_file = gen_dir / f"{slug}.md"
        if out_file.exists():
            skipped += 1
            continue

        profile = build_profile(sp, info["summary"], info["tax"])
        out_file.write_text(profile, encoding="utf-8")
        print(f"  ✓ {sci} -> {out_file.relative_to(ROOT)}")
        written += 1

    print(f"\nDone — {written} written, {skipped} skipped")


if __name__ == "__main__":
    main()
