#!/usr/bin/env python3
"""
FishBase enrichment for the species importer.

FishBase exposes official science-/taxonomy-grade tables as Apache parquet
files on Source Cooperative's S3 mirror:

    https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/cboettig/fishbase/fb/{version}/parquet/{table}.parquet

Two tables are used here:
  - species.parquet      -> per-species physical/life-history/habitat columns
                           (Length, CommonLength, Weight, LongevityWild,
                            DepthRangeShallow/Deep, Fresh/Brack/Saltwater,
                            DemersPelag)
  - occurrence.parquet   -> 1.1M museum/observation records with real
                           latitude/longitude per species, used to draw a
                           meaningful distribution map.

This module downloads those tables into a gitignored local cache on first use
(so reruns are fast and offline) and exposes lookups keyed by scientific name.
"""
from __future__ import annotations

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
                     "DemersPelag"],
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

    # -- lookups ----------------------------------------------------------

    def species_row(self, sci: str):
        self._load_species()
        return self._species.get(sci.strip().lower())

    def distribution_points(self, sci: str) -> list:
        self._load_points()
        return self._points.get(sci.strip().lower(), [])

    def table_paths(self) -> dict:
        self._load_species()
        self._load_points()
        return {"species": str(self._species_file), "occurrence": str(self._points_file)}


def build_fishbase_enrichment(fb: FishBase, sci: str) -> dict:
    """Return {physical, habitat_extra, points} enriched from FishBase."""
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
        shallow = row.get("DepthRangeShallow")
        deep = row.get("DepthRangeDeep")
        if shallow is not None or deep is not None:
            lo = int(shallow) if shallow is not None else 0
            hi = int(deep) if deep is not None else lo
            habitat_extra["depth_range_m"] = f"{lo}-{hi}"
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
