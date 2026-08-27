# Fishpedia

A public fishing encyclopedia combining scientific data (FishBase, FishFYI) with angling knowledge. Each species page features taxonomy, distribution maps, habitat, behavior, and fishing techniques.

## Structure

```
encyclopedia/
├── data/
│   ├── fish/{family}/{genus}/{species}.md   ← species profiles
│   ├── techniques/*.md                       ← fishing methods
│   └── gear/*.md                             ← equipment reference
├── templates/                                ← Jinja2 HTML templates
├── generate.py                               ← MD → HTML pipeline
└── out/                                      ← generated HTML
```

URLs follow taxonomy: `/fish/percidae/sander/zander/`

## Data Sources

| Source | Provides | Access |
|--------|----------|--------|
| [FishBase API](https://fishbase.org) | Taxonomy, biology, ecology, distribution | Free REST API |
| [FishFYI API](https://fishfyi.com/developers/) | Fishing methods, fight rating, bait, seasons | Free REST API |
| [FishRadar catalog](https://github.com/linkanlabs-ctrl/fishing-species-catalog) | Season months, conservation, aliases | CC BY 4.0 JSON |

## Quick Start

```bash
pip install pyyaml markdown-it-py jinja2
python3 encyclopedia/generate.py
open encyclopedia/out/fish/percidae/sander/zander.html
```

## Agent Configuration

See `AGENTS.md` for agent skills configuration.
See `docs/agents/` for issue tracker, triage labels, and domain docs.
