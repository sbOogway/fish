# Map: Fishing Encyclopedia

## Destination

A public fishing encyclopedia website where each species page combines FishBase scientific data, FishFYI angling data, and FishRadar seasonal/conservation data into a single HTML page with interactive Leaflet.js maps. 196 sport-fishing species for v1, taxonomy-based URL structure (`/fish/{family}/{genus}/{species}/`), hosted on GitHub Pages.

## Notes

- Domain: fishing / ichthyology / angling
- Data sources: FishBase API (free REST), FishFYI API (free REST, no auth), FishRadar catalog (CC BY 4.0 JSON on GitHub)
- Tech: Python pipeline (PyYAML, markdown-it-py, Jinja2), Leaflet.js maps, GitHub Pages
- Repo: github.com/sbOogway/fish
- Issue tracker: local markdown (`.scratch/`)
- Language: English for v1, extensible to Italian later

## Decisions so far

- Taxonomy-based structure: family/genus/species in URL, class/order in frontmatter only
- Encyclopedia only — no separate learning tracks
- On-demand FishBase API queries, not full ingestion
- Hybrid data: local markdown + links back to FishBase/FishFYI for images and references
- FishFYI API is free, no auth required — confirmed by testing
- FishRadar catalog (196 species) is the v1 species scope
- Fixed page template — same sections for every species
- Single page, all sections visible (no collapse, no sub-pages)
- Regulations out of scope for v1
- Leaflet.js with OpenStreetMap tiles for distribution maps
- GitHub Pages for hosting

## Not yet specified

- Data schema: exact YAML frontmatter format for merged fish profile (FishBase + FishFYI + FishRadar fields)
- Site generator: Hugo vs Eleventy vs custom Python generation
- Search and navigation: how users browse/filter species
- Deployment pipeline: GitHub Actions CI/CD workflow
- Multi-language architecture: how to add Italian later
- Technique and gear cross-referencing: how fish profiles link to technique pages
- Image licensing strategy: FishBase photos terms, Wikimedia Commons CC attribution format
- Species index page: how the homepage lists all 196 species

## Out of scope

- Regulations (varies by region, changes frequently — add in v2)
- Aquarium data (FishFYI has it, but not relevant to this encyclopedia's mission)
- Cuisine/cooking data (FishFYI has taste_description — out of scope for v1)
