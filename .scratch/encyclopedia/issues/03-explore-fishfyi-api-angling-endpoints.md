# 03 — Explore FishFYI API Angling Endpoints

Type: research
Status: open
Blocked by:

## Question

FishFYI has endpoints for fishing methods, seasonal entries, and water bodies. We need to understand what angling data is available per species and how to cross-reference it.

Specifically:
1. What does `/api/v1/methods/` return? Does each method list which species it's used for?
2. What does `/api/v1/seasons/` return? Is it per-species or per-region?
3. Can we query FishFYI by family to get all species in Percidae?
4. What is the image licensing policy? The API returns `image_url` pointing to Wikimedia Commons — can we use these directly?
5. Is there a rate limit?
6. Does the `.md` endpoint (append `.md` to any URL) work for API responses too?

This research unblocks the data schema (ticket 01) by telling us which FishFYI fields to include.
