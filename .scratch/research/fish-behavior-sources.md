# Sources for qualitative per-species angling behavior notes

Target species: **Sander lucioperca (zander, FishBase SpecCode 360)**
and **Silurus glanis (wels catfish, FishBase SpecCode 289)**.

Catalog size: 196 entries (`data/species.json`); 188 resolve to a FishBase
record; 179 of those are bony fish (others are cephalopods, crabs, etc.)
for which FishBase has no species row.

All data is drawn from the source's own primary surface (parquet mirror,
REST endpoint, raw HTML) — no secondary write-ups are cited.

---

## 1. FishBase parquet mirror (Source Cooperative)

- **Source**: cboettig/fishbase v25.04 parquet mirror — same data the
  FishBase web summary page renders, just a different transport.
  `https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/cboettig/fishbase/fb/v25.04/parquet/`
- **Local cache**: `encyclopedia/data/.fb_cache/*.parquet`
- **Importer**: `encyclopedia/fishbase.py` — currently reads 13 columns of
  `species.parquet` and 6 other biology tables.
- **License**: CC-BY-NC (`https://www.fishbase.se/copy.htm` — FishBase data
  is "open and free for non-commercial use" with attribution; the parquet
  mirror on Source Cooperative is the same data under the same terms).

### 1a. `species.Comments` — free-text biology paragraph (NOT currently imported)

- **Column**: `species.Comments` — a multi-sentence free-text paragraph
  covering habitat, diet, age at maturity, spawning time, migrations and
  human use. This is exactly the prose paragraph rendered as the "Biology"
  section on the FishBase web summary page
  (`https://www.fishbase.se/summary/360` — confirmed by fetching the
  rendered HTML: the "Biology" block is `Comments` verbatim).
- **Coverage**: populated for **178 of 179 fish (99%)** in our catalog.
- **License**: CC-BY-NC (FishBase).
- **Sander lucioperca (360)**:
  > "Adults inhabit large, turbid rivers and eutrophic lakes, brackish
  > coastal lakes and estuaries. Feed mainly on gregarious, pelagic fishes.
  > They attain first sexual maturity at 3-10 years of age, usually at 4.
  > Undertake short spawning migrations. … Spawn in pairs at dawn or
  > night. … Popularly fished by sport fishers."
- **Silurus glanis (289)**:
  > "Inhabits large and medium size lowland rivers, backwaters and well
  > vegetated lakes. … A nocturnal predator, foraging near bottom and in
  > water column. Larvae and juveniles are benthic, feeding on a wide
  > variety of invertebrates and fish. Adults prey on fish and other
  > aquatic vertebrates. …"
- **Verdict**: **usable**. 99% coverage on the 196-species catalog, free
  text already shaped like a behavior note, and the only known source
  for several of the specific behavioral facts the user cited
  ("near bottom and in water column", "gregarious, pelagic fishes",
  "Spawn in pairs at dawn or night"). Caveat: it is one paragraph and
  its scope (habitat + diet + reproduction + human use all together) is
  broader than the user asked for; some light editing or sentence-
  selection on the importer side would be needed to turn it into a
  per-species "Behavior" note.

### 1b. `species.DemersPelag` — water-column position (NOT currently used as prose)

- **Column**: `species.DemersPelag` — single value from a fixed vocabulary.
- **Coverage**: **179 of 179 fish (100%)**.
- **Sander lucioperca (360)**: `pelagic`.
- **Silurus glanis (289)**: `benthopelagic`.
- **Verdict**: **usable**. Only 6 distinct values across the whole
  catalog (e.g. `pelagic`, `benthopelagic`, `demersal`, `reef-associated`,
  `bathypelagic`), so it can drive a "stays in the water column" sentence
  in template form rather than free text.

### 1c. `species.BodyShapeI` — body shape (NOT currently imported)

- **Column**: `species.BodyShapeI` — single value, free text.
- **Coverage**: 179 of 179 fish (100%).
- **Sander lucioperca (360)**: `fusiform / normal`.
- **Silurus glanis (289)**: `elongated`.
- **Verdict**: **usable** for a small physical-behavior note ("elongated
  body", "fusiform predator"), but not a behavior field per se.

### 1d. `species.Dangerous` — danger to humans / status (NOT currently imported)

- **Column**: `species.Dangerous` — fixed vocabulary.
- **Coverage**: 178 of 179 fish (99%).
- **Values seen across the 179 species**: `harmless` (117), `reports of
  ciguatera poisoning` (28), `potential pest` (19), `traumatogenic` (8),
  `venomous` (3), `poisonous to eat` (2), `other` (1).
- **Sander lucioperca (360)**: `potential pest`.
- **Silurus glanis (289)**: `potential pest`.
- **Verdict**: **usable** for a single "danger to angler" sentence, but
  tangential to the user's stated wants (it is mostly about invasive
  status / human-harm potential rather than typical behavior).

### 1e. `species.AnaCat` — migratory behavior (NOT currently imported)

- **Column**: `species.AnaCat` — single value, fixed vocabulary.
- **Coverage**: 116 of 179 fish (65%) — the remainder are null.
- **Values seen across the 179 species**: `oceanodromous` (57),
  `potamodromous` (23), `anadromous` (15), `non-migratory` (10),
  `amphidromous` (6), `catadromous` (4), `oceano-estuarine` (1).
- **Sander lucioperca (360)**: `potamodromous`.
- **Silurus glanis (289)**: `non-migratory`.
- **Verdict**: **usable** for a one-word/one-line behavior tag (e.g.
  "migrates within rivers", "sea-run form", "non-migratory"). Skips
  35% of catalog species where the field is empty.

### 1f. `ecology.FeedingType` and `ecology.Herbivory2` — coarse feeding style (NOT currently imported; only structured ecology booleans are)

- **Columns**: `ecology.FeedingType`, `ecology.Herbivory2` — both short
  free-text fields.
- **Coverage (179 catalog fish with ecology rows = 181 ecology rows)**:
  `FeedingType` 171/181 (94%); `Herbivory2` 175/181 (97%).
- **Sander lucioperca (360)**: `FeedingType = "hunting macrofauna
  (predator)"`; `Herbivory2 = "mainly animals (troph. 2.8 and up)"`.
- **Silurus glanis (289)**: `FeedingType = "hunting macrofauna
  (predator)"`; `Herbivory2 = "mainly animals (troph. 2.8 and up)"`.
- **Verdict**: **usable** as a categorical tag for "predator that hunts
  larger prey" but coarse — only a handful of distinct values
  (`hunting macrofauna (predator)`, `grazing on aquatic plants`,
  `selective plankton feeding`, `variable`, etc.). Not the rich prose
  field the user described.

### 1g. `ecology.AddRems` — additional remarks narrative (NOT currently imported)

- **Column**: `ecology.AddRems` — free text, often 1–4 sentences about
  diet shifts, microhabitat, or local behavior observations.
- **Coverage**: **156 of 188 distinct species (83%)** in the 188-species
  catalog subset; 163 of 181 ecology rows.
- **Sander lucioperca (360)**:
  > "Ontogenetic changes in its food composition are quite pronounced.
  > Larvae measuring 6-8 mm consume small invertebrates. The consumption
  > of fish is observed at an average length of 29 mm. Characteristically
  > cannibalistic, particularly under conditions…"
- **Silurus glanis (289)**:
  > "Found in deep waters of dams constructed in the lower reaches of
  > rivers (Ref. 9696)."
- **Verdict**: **usable**. The most behavior-rich of the unstructured
  FishBase fields, and cites references inline that `Comments` does not
  always include. But variable in length (one short sentence to several
  paragraphs) and often locality-specific, so it is better as a
  supplemental remark than the primary behavior note.

### 1h. `ecology.Circadian*` / `BioAspect*` — diel activity (NOT currently imported)

- **Columns**: `ecology.Circadian1`/`2`/`3` (3 binary time-of-day slots
  in FishBase's controlled vocabulary) and `ecology.BioAspect1`/`2`/`3`
  (3 behavior aspects). Plus `RemarksCircadian` (free text, 16 rows in
  the whole FishBase of 12,675 ecology rows).
- **Coverage**: `Circadian1` 223/12,675 (1.8%), `BioAspect1` 223
  (1.8%); `RemarksCircadian` 16 (0.1%). For the 188 catalog species:
  1 of 181.
- **Sander lucioperca (360)**: all `Circadian*` and `BioAspect*` are 0/null.
- **Silurus glanis (289)**: all 0/null.
- **Verdict**: **not usable**. Effectively empty in the current
  FishBase release; do not rely on it for diel activity.

### 1i. `reproduc.AddInfos` — long reproduction narrative (already imported as `biology.reproduction`)

- **Column**: `reproduc.AddInfos` — already consumed by
  `build_biology` and rendered as the Biology section's "reproduction"
  paragraph.
- **Sander lucioperca (360)**: "The spawning places are over gravel in
  moving water … Males are territorial and excavate shallow depressions
  about 50 cm in diameter and 5-10 cm deep in sand or gravel… Spawn in
  pairs, at dawn or night…"
- **Silurus glanis (289)**: "Males defend small territories in the
  spawning sites and construct nests made of plant materials… Males
  guard the nests until larvae emerge. Spawns in pairs…"
- **Verdict**: **usable** for spawning-behavior content specifically
  (it is the source of the "spawn in pairs at dawn or night" / "males
  guard nest" facts). But the field is reproduction-only, so on its
  own it doesn't cover the broader "where it sits in the water column /
  how aggressive it is / daily activity" set the user described.

### 1j. `diet.parquet` — monthly feeding matrix (NOT currently imported)

- **Columns**: 12 month columns (binary 0 / -1, with `-1` meaning
  "feeding observed this month"), `Remark`, `OtherItems`, `PercentEmpty`,
  `Troph`, `seTroph`, `SampleStage`, `Locality`, etc.
- **Sander lucioperca (360)**: 13 rows, but the Jan–Dec columns are all
  0 (the `-1`s appear in only a handful of rows; the field is not
  consistently populated as a "monthly feeding" signal).
- **Silurus glanis (289)**: 3 rows, all 12 month columns = 0.
- **Verdict**: **not usable**. The monthly feeding matrix is mostly
  empty in v25.04; the data was not migrated correctly. Skip.

### 1k. `spawning.AddInfos` (already imported as part of `biology.spawning_months` aggregation)

- **Sander lucioperca (360)**: "Spawns in spring. Maximum fecundity is
  2,500,000 eggs. … Spawns in relatively deep water. Eggs are deposited
  on the gravel and sand and are guarded by the male."
- **Silurus glanis (289)**: "Eggs are deposited on a depression in the
  bottom and are guarded by the males. May also spawn in the swampy
  regions of lakes. … Spawns in northern areas until August when
  temperature reaches about 20°C."
- **Verdict**: **usable** for spawning-behavior micro-facts (depth,
  substrate, parental behavior) but is not the primary behavior field.

### 1l. FishBase web summary page (not a separate source)

- The "Ecology" / "Biology" / "Environment" prose blocks on
  `https://www.fishbase.se/summary/{SpecCode}` are rendered from the
  same `species.Comments` / `species.AnaCat` / `species.DemersPelag` /
  `ecology.AddRems` columns already present in the parquet. Fetching
  the page and stripping HTML returned the exact same sentences.
- **Verdict**: **not usable** as a separate source. The parquet mirror
  already gives us the same data without Cloudflare challenges (see the
  note in `encyclopedia/data/fish-profile-schema.yaml:150-152` about
  fishbase.org being Cloudflare-challenged).

---

## 2. FishRadar catalog (`data/species.json`)

- **Source**: `https://raw.githubusercontent.com/linkanlabs-ctrl/fishing-species-catalog/main/data/species.json`
- **Importer**: `encyclopedia/import_species.py:133-134` (`load_fishradar`).
- **License**: per the upstream repo — not declared in the JSON itself.
- **Schema** (re-verified by scanning all 196 entries; the union of keys
  is exactly nine):
  `id`, `scientific`, `english`, `aliases`, `environment`, `latRange`,
  `seasonMonths`, `seasonMonthsHemisphereNote`, `conservationStatus`.
  No free-text fields beyond the common-name string. No behavior notes,
  no description, no habitat/season prose.
- **Sander lucioperca** (in catalog as `zander`): has only
  `seasonMonths: [3,4,5,6,7,8,9,10,11]`, `environment: "freshwater"`,
  `latRange: [35, 67]`. No behavior string.
- **Silurus glanis** (in catalog as `wels-catfish`): same shape, no
  behavior string.
- **Verdict**: **not usable** for behavior notes — the catalog carries
  no free-text fields at all. It is purely an identity + season index.

---

## 3. FishFYI (`fishfyi.com`)

- **Source**: `https://www.fishfyi.com/fish/{slug}` (the slug matches
  FishRadar `id`, e.g. `/fish/zander`, `/fish/wels-catfish`).
  Embeddable widget and iframe offered; no public REST API endpoint is
  documented on the page.
- **License**: © 2026 FishFYI (proprietary; no CC / public-domain
  statement on the page).
- **What it actually carries per species** (per the rendered HTML):
  - An **"Overview"** paragraph (1–2 sentences; this is the closest to
    a free-text behavior note — explicitly says "crepuscular predator"
    for zander, "highly nocturnal … hunts largely by night" for wels).
  - An **"About"** paragraph (1 sentence, largely a restatement of the
    Overview).
  - Structured fact cards: Max Length / Max Weight / Color / Depth Range
    / Family / Category / Conservation Status.
  - A "Fishing Information" block with `Game Fish: Yes`, `Fight Rating
    6/5` (zander) / `9/5` (wels), `Recommended Bait: "soft plastics,
    jigs, live baitfish"` (zander) / `"live baitfish, large lures,
    worms"` (wels).
  - Country list, taxonomy, other-language names, FAQ (which is just
    prose restating the fact cards).
- **Sander lucioperca (zander) — Overview**:
  > "Often called the European counterpart of the walleye, the zander
  > is a slender, greenish percid whose large, light-gathering eyes
  > make it a crepuscular predator. … It tolerates mildly brackish
  > conditions in the Baltic and Caspian margins and hunts most
  > actively at dawn and dusk. …"
- **Silurus glanis (wels-catfish) — Overview**:
  > "The largest freshwater fish in Europe, the wels catfish can
  > exceed five metres and 300 kilograms … it hunts largely by night.
  > … It has been filmed lunging onto shorelines to seize bathing
  > pigeons. …"
- **Coverage**: appears to cover all 196 catalog entries (every FishRadar
  `id` resolves to a FishFYI page; no public coverage report).
- **Verdict**: **not usable**. This is the source the user already
  ruled out for the species page content; the Overview is the only
  field that would fit the request, and it is not extractable via a
  public API, is rendered in client-side React (the raw HTML returned
  by `https://www.fishfyi.com/fish/zander` is mostly the app shell
  with the prose inside server-rendered `<p>` blocks), and is
  copyrighted. The Fight Rating, Recommended Bait, and Game Fish fields
  are interesting angling metadata, but the import pipeline already
  routes them through FishBase and the rest of the page is editorial
  prose. The user explicitly excluded FishFYI.

---

## 4. Wikipedia REST API

- **Source A (already used)**: `https://en.wikipedia.org/api/rest_v1/page/summary/{title}`
  — already imported into `meta.description` (see
  `encyclopedia/import_species.py:89-94`). Returns an `extract` string
  (the lead paragraph).
- **Source B**: `https://en.wikipedia.org/api/rest_v1/page/html/{title}`
  and `https://en.wikipedia.org/api/rest_v1/page/mobile-html/{title}` —
  full rendered article HTML. **NOT** currently imported.
- **Source C**: `https://en.wikipedia.org/w/api.php?action=parse&page=…`
  (the MediaWiki parse API) — returns structured `wikitext` with
  `sections[*].line` headings. **NOT** currently imported.
- **License**: CC-BY-SA 4.0 (`https://en.wikipedia.org/wiki/Wikipedia:Copyrights`).

### 4a. `page/summary` — `extract` (already imported)

- The lead extract is a single paragraph and is currently used as
  `meta.description`. It is *not* a behavior note — it usually covers
  identity and range.
- **Sander lucioperca** lead:
  > "The zander, sander or pikeperch, is a species of ray-finned fish
  > from the family Percidae. It is found in freshwater and brackish
  > habitats in western Eurasia. As a popular game fish, it has been
  > introduced to a variety of localities outside its native range. It
  > is the type species of the genus Sander."
- **Silurus glanis** lead:
  > "The wels catfish, also called sheatfish or just wels, is a large
  > species of catfish native to wide areas of central, southern, and
  > eastern Europe, in the basins of the Baltic, Black and Caspian Seas.
  > It has been introduced to several countries in Western Europe,
  > Mediterranean and Asia as a prized sport fish."
- **Verdict**: **not usable** as a behavior source — the lead is
  identity/range prose, not behavior. (Could only be the source of
  behavior facts by mining the full article — see 4b.)

### 4b. `page/html` / `page/mobile-html` — full article HTML (NOT currently imported)

- Returns the full article including section headings. The
  `Habitat`/`Diet`/`Reproduction`/`Life history`/`Distribution and
  ecology` sections are exactly the structure that yields angling
  behavior facts.
- **Sander lucioperca** ("Habitat" and "Diet" sections, rendered):
  > "Zander inhabit freshwater bodies, especially large rivers and
  > eutrophic lakes. … Zander are carnivorous and the adults feed on
  > smaller schooling fish. … They cannibalize smaller zanders. …
  > In the United Kingdom, zander thrive in canals, where the water is
  > turbid due to boat traffic."
  >
  > Reproduction: "Spawning takes place in pairs, at night and at
  > daybreak. … The male remains at the nest and defends it, fanning
  > the eggs using the pectoral fins. … The larvae are attracted to
  > light, and after they leave the nest they feed on zooplankton and
  > small pelagic animals."
- **Silurus glanis** ("Description" and "Diet" and "Distribution and
  ecology" sections, rendered):
  > "The wels relies largely on hearing and smell for hunting prey …
  > With its sharp pectoral fins, it creates an eddy to disorient its
  > victim, which the predator sucks into its mouth and swallows whole.
  > …"
  >
  > "Like most freshwater bottom feeders, the wels catfish lives on
  > annelid worms, gastropods, insects, crustaceans and fish. Larger
  > specimens have also been observed to eat crayfish, eels, frogs,
  > snakes, rats, voles, coypu and aquatic birds such as ducks, even
  > cannibalising on other catfish. … 28% of the beaching behaviour
  > observed and filmed in this study were successful in bird capture."
  >
  > "The wels catfish lives in large, warm lakes and deep, slow-flowing
  > rivers. It prefers to remain in sheltered locations such as holes in
  > the riverbed, sunken trees, etc. …"
- **Coverage**: every species with a Wikipedia article (the lead extract
  is non-empty for most of the 196; per the existing
  `import_species.py:362-365` check, those without a Wikipedia page are
  skipped, so the effective ceiling is the same as the existing import).
- **Verdict**: **investigate further**. The full Wikipedia article
  contains the richest free-text behavior content of any source we
  surveyed — exactly the "zander are carnivorous and feed on smaller
  schooling fish … cannibalize smaller zanders" / "wels prefers holes
  in the riverbed, hunts largely by night, lunges onto shorelines to
  seize pigeons" type of fact. The cost is moving from the cheap
  `page/summary` JSON to a much larger HTML payload (the zander
  article is ~30 KB rendered; wels is ~25 KB) and sectioning it. Two
  viable patterns: (a) use `page/mobile-html` and grep the
  "Habitat"/"Diet"/"Reproduction"/"Behaviour" `<h2>` sections, or
  (b) use `action=parse` and pull the `sections[*].line` map to find
  the right ones. The user already pulls the lead as `description`; a
  behavior-mining pass on the same page would be the natural extension.

### 4c. No other structured field on `page/summary`

- The summary response carries only `title`, `displaytitle`, `wikibase_item`,
  `description` (a short topical tag like "Species of fish", not
  behavior), `extract`, `extract_html`, `thumbnail`, `originalimage`,
  `content_urls`, `lang`, `dir`, `timestamp`, `revision`, `tid`. No
  behavior / habitat / feeding fields.

---

## 5. Wikidata (P-statements on Q146641 / Q159323)

- **Source**: `https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={QID}`
- **License**: CC0 (`https://www.wikidata.org/wiki/Wikidata:Licensing`).
- **Existing import**: `encyclopedia/import_species.py:111-130`
  (`wikidata_taxonomy`) only reads P171/P105 (ancestor + rank) to
  populate `class`/`order`/`family`/`genus`.

### 5a. Property inventory on Q146641 (zander) and Q159323 (wels)

- Q146641 carries **60 P-statements**, all of them cross-reference
  identifiers (FishBase, NCBI, ITIS, GBIF, WoRMS, IUCN, iNaturalist,
  EUNIS, etc.) or taxonomy labels (P225, P171, P105, P181, P1843,
  P4024). There is no P-statement on Q146641 that describes habitat,
  diet, behavior, water-column position, aggression, or daily activity.
- A targeted check of biology-relevant properties on both Q146641 and
  Q159323 returned **no claims** for:
  P2974 (trophic level), P1034 (diet), P2067 (mass), P1050 (medical
  condition treated), P3489 (feeds on), P5052 (temperature), P1004
  (instrument), P181, P3132.
- Q159323 is not in the previously cached dump (Q146641 only); a fresh
  fetch with the same biology-relevant property list also returned no
  claims.
- **Coverage**: among 196 catalog species, those with a Wikipedia page
  almost all have a Wikidata item, but the items in turn only carry
  identifiers and taxonomy — no behavior fields.
- **Verdict**: **not usable**. Wikidata has no P-property that
  captures water-column position, aggression, or daily activity for
  fish taxa, and the two sample items confirm the gap.

---

## Summary table

| # | Source | Free-text behavior? | Coverage on 196 | License | Verdict |
|---|---|---|---|---|---|
| 1a | FishBase `species.Comments` | yes (paragraph) | 99% of fish (178/179) | CC-BY-NC | **usable** |
| 1b | FishBase `species.DemersPelag` | no (enum) | 100% | CC-BY-NC | usable (template) |
| 1c | FishBase `species.BodyShapeI` | short text | 100% | CC-BY-NC | usable (small) |
| 1d | FishBase `species.Dangerous` | enum | 99% | CC-BY-NC | usable (tangential) |
| 1e | FishBase `species.AnaCat` | enum | 65% | CC-BY-NC | usable (partial) |
| 1f | FishBase `ecology.FeedingType` / `Herbivory2` | short text | 94–97% | CC-BY-NC | usable (coarse) |
| 1g | FishBase `ecology.AddRems` | yes (1–4 sentences) | 83% | CC-BY-NC | usable |
| 1h | FishBase `ecology.Circadian*` / `BioAspect*` | enum | ~1% | CC-BY-NC | not usable |
| 1i | FishBase `reproduc.AddInfos` | yes | already imported | CC-BY-NC | usable (spawning only) |
| 1j | FishBase `diet.parquet` | monthly matrix | mostly empty | CC-BY-NC | not usable |
| 1k | FishBase `spawning.AddInfos` | yes | already imported | CC-BY-NC | usable (spawning only) |
| 1l | FishBase web summary page | same as 1a | same | CC-BY-NC | not usable (duplicate) |
| 2 | FishRadar `data/species.json` | no | 196/196 | upstream (not declared) | not usable |
| 3 | FishFYI `fishfyi.com/fish/{slug}` | yes (Overview paragraph) | ~196 | proprietary | not usable (user ruled out) |
| 4a | Wikipedia `page/summary` `extract` | yes (lead) | most | CC-BY-SA 4.0 | not usable (identity prose) |
| 4b | Wikipedia `page/html` / `page/mobile-html` (Habitat / Diet / Reproduction sections) | yes | most | CC-BY-SA 4.0 | **investigate further** |
| 5 | Wikidata P-statements | no behavior P-properties | most | CC0 | not usable |

**Headline**: the strongest drop-in source is **FishBase
`species.Comments`** (1a) — 99% coverage, free text, already in the
parquet cache, no new fetch needed. For richer angler behavior
("nocturnal, lunges for pigeons", "spawns at dawn, defends nest")
the **Wikipedia full-article Habitat/Diet/Reproduction sections** (4b)
are richer than anything FishBase offers and the only realistic path
to "zander like to stay in the bottom / wels will attack almost
anything"-style notes.
