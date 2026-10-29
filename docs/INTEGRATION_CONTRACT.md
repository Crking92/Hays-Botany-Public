# Hays Botany Hub — non-destructive integration contract

**Status:** starter preview only. `Hays-Botany-Public` is not the present public learner; the live original site remains `https://crking92.github.io/Hays-County-Botany/`. No GitHub Pages deployment is configured here.

## Scope of this initial setup

- One read-only `data/species-index.json` is derived from the original source `data/manifest.json` and records the pinned source manifest Git blob SHA and each stable ID, path, genus and family.
- `data/collections.json` records all 146 family assignments into 10 repositories. Every collection is explicitly `NOT_LIVE`; there are no approved family Pages URLs.
- The hub search is functional for stable IDs, derived scientific search labels, genera and families. **Common names and up-to-date accepted taxonomic presentation still require a verified per-species metadata export.** Do not treat guessed labels or source IDs as an accepted-name taxonomic audit.
- All search result links intentionally lead to the **original working learner** using `?species=<id>`. Family buttons filter the local index; staging collection cards link only to the corresponding GitHub repository.
- No third-party photo assets are copied into the public hub. Use audited image-level attribution and publication approval before adding media. The preview currently avoids the need for that entirely.
- The Visual Learner, Field ID, glossary and quiz buttons open the existing original site. They are not falsely represented as independent finished implementations.

## Local preview

From the repository root run `python -m http.server 8000`, then visit `http://127.0.0.1:8000/`. Static browser fetches require HTTP; opening `index.html` using `file://` will not load JSON in most browsers.

Run `python scripts/validate_hub.py` to check inventory/family mapping, source snapshot and that all family sites stay unpublished. GitHub Actions runs that validation and Node's JavaScript syntax check on every push/PR. The workflow does **not** publish Pages.

## Before the eventual real hub release

1. Generate and review accepted scientific names, common names, aliases, genus look-alikes and family metadata from verified canonical source records — not from labels derived from stable IDs alone. Build a repeatable read-only export, preserving original source SHA and checking source freshness.
2. Confirm family collection Pages URLs from actual successful deployments. A destination repo's existence or passing preview is insufficient. Maintain original fallback for any not-live family.
3. Test all-family search, direct `?species=` links, browser Back, accessibility, mobile touch scrolling, consistent design, glossary/quiz links, family/genus browsing, and attribution.
4. Verify public repo entire asset history and individual photograph rights before publishing any images. Never leak NC/permission-limited/private-only original photos merely because a website build filters them.
5. Explicitly approve and test release, source ownership transfer, reversible hub routing, rollback and safe links; only then update `live_url` fields and turn on production routes. Original website stays available until separately approved replacement.

Shared coordination: [current multi-repo rules](https://github.com/Crking92/Hays-County-Botany/blob/main/workflow/MULTI_REPO_OPERATING_RULES_20261028.md).
