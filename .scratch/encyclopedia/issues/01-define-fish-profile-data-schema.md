# 01 — Define Fish Profile Data Schema

Type: grilling
Status: open
Blocked by: 03

## Question

What is the exact YAML frontmatter format for a merged fish profile? This schema must accommodate fields from three sources:

- **FishBase API**: taxonomy (class, order, family, genus, species), physical (max_length_cm, max_weight_kg, lifespan), habitat (water_types, depth_range, substrate, temperature), ecology (feeding type, diet, peak times, schooling, spawning), distribution (regions with coordinates)
- **FishFYI API**: fight_rating, best_bait, fishing_methods, color_description, geographic_range, conservation_status, image_url, fishbase_id
- **FishRadar catalog**: seasonMonths, latRange, conservationStatus, aliases

The schema should be a single YAML frontmatter block in each `fish/{family}/{genus}/{species}.md` file, with a markdown body below for longer-form descriptions.

Key decisions:
1. Which fields are required vs optional?
2. How to handle fields that overlap (e.g. max_length from FishBase vs FishFYI)?
3. How to structure distribution coordinates for Leaflet.js?
4. How to store technique/gear references (links to technique pages)?
5. How to handle the image (URL + credit + license)?
