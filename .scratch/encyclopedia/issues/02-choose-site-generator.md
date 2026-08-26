# 02 — Choose Site Generator

Type: research
Status: open
Blocked by:

## Question

What static site generator or build tool should we use to turn the markdown encyclopedia into a public website on GitHub Pages?

Options to evaluate:
- **Hugo**: fast, Go-based, large ecosystem, good GitHub Pages support
- **Eleventy (11ty)**: JavaScript-based, flexible, good for data-driven sites
- **Custom Python**: extend existing `generate.py`, no framework dependency
- **Gatsby/Next.js**: overkill for a content site, but powerful

Evaluation criteria:
1. GitHub Pages deployment (native or via GitHub Actions)
2. Template flexibility (Jinja2-like syntax preferred since we already use it)
3. Search capability (client-side or built-in)
4. Leaflet.js integration (static HTML pages with embedded maps)
5. Ease of adding new species (just add a markdown file?)
6. Build speed (196 pages is small, but still)
7. Multi-language support (future: English + Italian)
