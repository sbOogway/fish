# Fishpedia

A public fishing encyclopedia combining scientific data (FishBase, FishFYI, FishRadar) with angling knowledge. Each species page features taxonomy, distribution maps, habitat, behavior, and fishing. Species pages are auto-generated from the FishRadar catalog enriched with Wikipedia/Wikidata — see `docs/adr/0002-species-data-pipeline.md`.

## Structure

```
encyclopedia/
├── data/
│   └── fish/{family}/{genus}/{id}.md   ← species profiles (.md + frontmatter)
├── templates/                          ← Jinja2 HTML templates
├── generate.py                         ← MD → HTML pipeline
├── import_species.py                   ← FishRadar + Wikipedia/Wikidata importer
└── out/                                ← generated HTML (gitignored)
```

## Data Sources

| Source | Provides | Access |
|--------|----------|--------|
| [FishBase API](https://fishbase.org) | Taxonomy, biology, ecology, distribution | Free REST API |
| [FishFYI API](https://fishfyi.com/developers/) | Fishing methods, fight rating, bait, seasons | Free REST API |
| [FishRadar catalog](https://github.com/linkanlabs-ctrl/fishing-species-catalog) | 196 species, aliases, environment, season months, conservation | CC BY 4.0 JSON |
| [Wikipedia / Wikidata](https://en.wikipedia.org) | Lead prose, hero image, family/genus/order/class | Free REST + SPARQL APIs |

## Regenerate / add species

```bash
unset ALL_PROXY all_proxy http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
uv run python3 encyclopedia/import_species.py   # fetch all 196 into data/fish/
uv run python3 encyclopedia/generate.py          # build HTML into out/
```

The importer is idempotent: it skips species that already have a hand-crafted profile (matched by scientific name), so curated pages are never overwritten. External lookups are cached so reruns are fast.

## Quick Start

```bash
pip install pyyaml markdown-it-py jinja2
python3 encyclopedia/generate.py
open encyclopedia/out/percidae/sander/zander.html
```

## Agent Configuration

See `AGENTS.md` for agent skills configuration.
See `docs/agents/` for issue tracker, triage labels, and domain docs.
