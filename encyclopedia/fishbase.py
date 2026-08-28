#!/usr/bin/env python3
"""
FishBase enrichment for the species importer.

FishBase exposes official science-/taxonomy-grade tables as Apache parquet
files on Source Cooperative's S3 mirror:

    https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/cboettig/fishbase/fb/{version}/parquet/{table}.parquet

Several tables are used here, all keyed (where relevant) by `SpecCode`
(= the species' source id, cross-referenced as `sources.fishbase_id`):

  - species.parquet      -> per-species physical/life-history/habitat columns
                           (Length, CommonLength, Weight, LongevityWild,
                           DepthRangeShallow/Deep, Fresh/Brack/Saltwater,
                           DemersPelag). Keyed by `SpecCode`.
  - occurrence.parquet   -> 1.1M museum/observation records with real
                           latitude/longitude per species, used to draw a
                           meaningful distribution map. Keyed by name.
  - reproduc.parquet     -> reproduction biology narrative (`AddInfos`) plus
                           mode/fertilization/parental-care facts.
  - spawning.parquet     -> monthly spawning matrix (+ per-locale fecundity).
  - fecundity.parquet    -> per-locale egg counts.
  - maturity.parquet     -> age/length at maturity.
  - fooditems.parquet    -> recorded diet/prey items.
  - predats.parquet      -> recorded predators.

Biology tables are keyed by `SpecCode` (== `sources.fishbase_id`), so this
module exposes lookups both by scientific name and by SpecCode.

This module downloads those tables into a gitignored local cache on first use
(so reruns are fast and offline).
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "encyclopedia" / "data"
CACHE_DIR = DATA_DIR / ".fb_cache"

FB_VERSION = "v25.04"
FB_BASE = ("https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/"
           "cboettig/fishbase/fb/" + FB_VERSION + "/parquet")

USER_AGENT = "FishpediaImporter/1.0 (fishing encyclopedia builder; contact: mattia@example.com)"

# Maximum number of distribution points to embed per species (keep JSON + map snappy).
MAX_POINTS = 220

# windowing/section building helpers -----------------------------------------

# FishBase citation noise: (Ref. 205), (Refs. 7471, 51442), (Ref. 7471; 51442).
_REF_RE = re.compile(r"\s*\((?:Refs?\.?)\s*[\d,\s;]+\)")

_MONTH_COLS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def strip_citations(text: str) -> str:
    """Remove FishBase `(Ref. NNNNN)` citation markers from a narrative."""
    if not text:
        return text
    out = _REF_RE.sub(" ", text)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def _download(name: str) -> Path:
    """Download a parquet table into the cache if not already present."""
    dest = CACHE_DIR / f"{name}.parquet"
    if dest.exists():
        return dest
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{FB_BASE}/{name}.parquet"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    print(f"  [fishbase] downloading {name}.parquet ...")
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest


class FishBase:
    """Lazy-loaded FishBase enrichment lookups keyed by scientific name."""

    def __init__(self):
        self._species = None  # {scientific_lower: row}
        self._points = None   # {scientific_lower: [[lat, lng], ...]}
        self._species_file = None
        self._points_file = None
        self._by_code = None  # {SpecCode: {table: [rows]}} lazily populated

    # -- loading ----------------------------------------------------------

    def _load_species(self):
        if self._species is not None:
            return
        self._species_file = _download("species")
        t = pq.read_table(
            str(self._species_file),
            columns=["SpecCode", "Genus", "Species", "Length", "CommonLength",
                     "Weight", "LongevityWild", "DepthRangeShallow",
                     "DepthRangeDeep", "Fresh", "Brack", "Saltwater",
                     "DemersPelag", "Comments"],
        )
        self._species = {}
        for r in t.to_pylist():
            g = (r["Genus"] or "").strip()
            s = (r["Species"] or "").strip()
            if g and s:
                self._species[(g + " " + s).lower()] = r

    def _load_points(self):
        if self._points is not None:
            return
        self._points_file = _download("occurrence")
        t = pq.read_table(
            str(self._points_file),
            columns=["GenusCol", "SpeciesCol", "LatitudeDec", "LongitudeDec"],
        )
        buckets: dict[str, list] = {}
        for r in t.to_pylist():
            lat, lng = r["LatitudeDec"], r["LongitudeDec"]
            if not lat or not lng:
                continue
            g = (r["GenusCol"] or "").strip()
            s = (r["SpeciesCol"] or "").strip()
            if not g or not s:
                continue
            key = (g + " " + s).lower()
            # Round to ~110m grid and drop duplicates so each cell counts once.
            pt = (round(lat, 3), round(lng, 3))
            buckets.setdefault(key, set()).add(pt)
        # Deterministic downsample, space-dispersed rather than random.
        self._points = {}
        for key, pts in buckets.items():
            pts = sorted(pts)
            if len(pts) > MAX_POINTS:
                step = len(pts) / MAX_POINTS
                pts = [pts[int(i * step)] for i in range(MAX_POINTS)]
            self._points[key] = pts

    def _load_by_code(self):
        """Load the biology tables, bucketed per SpecCode."""
        if self._by_code is not None:
            return
        self._by_code = {}

        def table_rows(name, code_col):
            p = _download(name)
            t = pq.read_table(str(p))
            rows = t.to_pylist()
            buckets = {}
            for r in rows:
                code = r.get(code_col)
                if code is None:
                    continue
                buckets.setdefault(code, []).append(r)
            return buckets

        specs = {
            "reproduc": "SpecCode",
            "spawning": "SpecCode",
            "fecundity": "SpecCode",
            "maturity": "Speccode",
            "fooditems": "SpecCode",
            "predats": "SpecCode",
        }
        for table, code_col in specs.items():
            data = table_rows(table, code_col)
            for code, rows in data.items():
                self._by_code.setdefault(code, {})[table] = rows

    def code_tables(self, spec_code):
        """Return {table: [rows]} for a SpecCode (empty dict if unknown)."""
        self._load_by_code()
        return self._by_code.get(spec_code, {})


    # -- lookups ----------------------------------------------------------

    def species_row(self, sci: str):
        self._load_species()
        return self._species.get(sci.strip().lower())

    def species_comments(self, sci: str) -> str:
        """Return the free-text `species.Comments` paragraph for a scientific name, or ''."""
        row = self.species_row(sci)
        if not row:
            return ""
        text = row.get("Comments")
        return text.strip() if text else ""

    def distribution_points(self, sci: str) -> list:
        self._load_points()
        return self._points.get(sci.strip().lower(), [])

    def table_paths(self) -> dict:
        self._load_species()
        self._load_points()
        self._load_by_code()
        return {"species": str(self._species_file), "occurrence": str(self._points_file)}


def build_fishbase_enrichment(fb: FishBase, sci: str) -> dict:
    """Return {physical, habitat_extra, points} enriched from FishBase.

    The `physical` block holds the v2 fact-sheet dimensions (max_length_cm,
    typical_length_cm, max_weight_kg) plus `lifespan_years` (which the v2
    importer pops out and into the top-level `facts` block). Depth range is
    dropped in v2 (low coverage; fact-sheet does not need it).
    """
    row = fb.species_row(sci)
    physical = {}
    habitat_extra = {}
    if row:
        if row["Length"]:
            physical["max_length_cm"] = round(row["Length"])
        if row["CommonLength"]:
            physical["typical_length_cm"] = str(round(row["CommonLength"]))
        if row["Weight"]:
            physical["max_weight_kg"] = round(row["Weight"] / 1000.0, 1)
        if row["LongevityWild"]:
            physical["lifespan_years"] = str(round(row["LongevityWild"]))
        if row.get("DemersPelag"):
            habitat_extra["body_ecology"] = row["DemersPelag"].strip()
        flags = []
        if row["Fresh"]:
            flags.append("freshwater")
        if row["Brack"]:
            flags.append("brackish")
        if row["Saltwater"]:
            flags.append("saltwater")
        if flags:
            habitat_extra["water_types"] = flags

    return {
        "physical": physical,
        "habitat": habitat_extra,
        "points": fb.distribution_points(sci),
    }


def _spawning_months(rows):
    """Return sorted 1-12 month indices forming the dominant spawning season.

    A month counts once per spawning record if marked active; months that appear
    in at least half as many records as the peak month are kept. This isolates
    the primary season and ignores incidental/outlier records with near-year-round
    coverage.
    """
    counts = [0] * 13
    for r in rows:
        active = any(r.get(col) is not None and float(r[col]) > 0 for col in _MONTH_COLS)
        if not active:
            continue
        for i, col in enumerate(_MONTH_COLS, start=1):
            v = r.get(col)
            if v is not None and float(v) > 0:
                counts[i] += 1
    peak = max(counts)
    if peak <= 0:
        return []
    return [i for i in range(1, 13) if counts[i] >= peak / 2]


def _fecundity_range(rows):
    """Return a representative 'min-max eggs' range, or None.

    Collects every reported egg count (min and max) across fecundity/spawning
    records and trims to the 15th-85th percentile so a single outlying locality
    doesn't blow the range out.
    """
    counts = []
    for table in ("fecundity", "spawning"):
        for r in rows.get(table, []):
            for k in ("FecundityMin", "FecundityMax"):
                v = r.get(k)
                if v:
                    counts.append(float(v))
    if not counts:
        return None
    counts.sort()
    lo = int(counts[int(len(counts) * 0.15)])
    hi = int(counts[min(len(counts) - 1, int(len(counts) * 0.85))])
    if hi <= lo:
        return f"{hi:,} eggs"
    return f"{lo:,}-{hi:,} eggs"


def _age_maturity(rows):
    """Return an age at maturity string from the maturity table, or None.

    Uses the median first-maturity age (`tm`) reported across studies, rounded
    to the nearest half-year, as the representative figure. Falls back to the
    recorded age-at-maturity span when no `tm` value exists.
    """
    mat = rows.get("maturity", [])
    tms = sorted(float(r["tm"]) for r in mat if r.get("tm") is not None and float(r["tm"]) > 0)
    if tms:
        med = tms[len(tms) // 2]
        yr = int(round(med))
        if abs(med - yr) <= 0.26:
            return f"{yr} years"
        half = 0.5 * round(med / 0.5)
        half = int(half) if half == int(half) else half
        return f"{half} years"
    los = [float(r["AgeMatMin"]) for r in mat if r.get("AgeMatMin") is not None]
    his = [float(r["AgeMatMin2"]) for r in mat if r.get("AgeMatMin2") is not None]
    if los and his:
        return f"{int(min(los))}-{int(max(his))} years"
    if los:
        return f"{int(min(los))} years"
    return None


def _diet_items(rows):
    """Distinct prey categories (FoodIII, else FoodII) from fooditems."""
    PH = {
        "plank. copepods": "copepods",
        "plank. crustaceans": "planktonic crustaceans",
        "plank. invertebrates": "planktonic invertebrates",
        "fish eggs/larvae": "fish eggs & larvae",
        "shrimps/prawns": "shrimps & prawns",
    }
    DROP = ("n.a./", "n.a. ", "n.a.", "others")
    found = set()
    for r in rows.get("fooditems", []):
        item = r.get("FoodIII") or r.get("FoodII")
        if not item:
            continue
        item = item.strip()
        item = PH.get(item, item)
        if item.lower().startswith("n.a."):
            continue
        found.add(item.capitalize())
    return sorted(found)


def _predator_names(rows):
    """Distinct predator species names from predats."""
    names = {r.get("PredatorName") for r in rows.get("predats", [])}
    names = {n.strip() for n in names if n and n.strip().lower() != "unidentified"}
    return sorted(names)


def build_biology(fb: FishBase, spec_code: int | None) -> dict:
    """Build the `biology` enrichment block from the FishBase biology tables.

    Returns a dict with optional keys: reproduction (narrative), repro_mode,
    fertilization, parental_care, spawning_months, fecundity, age_maturity,
    diet, predators. Absent keys mean no data for that facet.
    """
    if not spec_code:
        return {}
    tables = fb.code_tables(spec_code)
    if not tables:
        return {}

    out = {}

    repro = tables.get("reproduc", [])
    narratives = [strip_citations(r["AddInfos"]) for r in repro if r.get("AddInfos")]
    if narratives:
        out["reproduction"] = " ".join(narratives)
    mode = next((r["ReproMode"] for r in repro if r.get("ReproMode")), None)
    fert = next((r["Fertilization"] for r in repro if r.get("Fertilization")), None)
    care = next((r["ParentalCare"] for r in repro if r.get("ParentalCare")), None)
    if mode:
        out["repro_mode"] = mode
    if fert:
        out["fertilization"] = fert
    if care:
        out["parental_care"] = care

    spawn = tables.get("spawning", [])
    months = _spawning_months(spawn)
    if months:
        out["spawning_months"] = months

    fec = _fecundity_range(tables)
    if fec:
        out["fecundity"] = fec

    # `age_maturity` is computed here (because the maturity table lives in
    # FishBase) but in v2 it lives in the top-level `facts` block; the
    # importer pops it out of the biology dict and into facts.
    age = _age_maturity(tables)
    if age:
        out["age_maturity"] = age

    diet = _diet_items(tables)
    if diet:
        out["diet"] = diet

    preds = _predator_names(tables)
    if preds:
        out["predators"] = preds

    return out
