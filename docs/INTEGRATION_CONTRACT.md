# Hays Botany — current family hub integration contract

**Updated October 30, 2026 — existing-data migration complete, public cross-family learner verified, new source-data intake approved only through family repositories.**

This repository is the **separate public cross-family hub** at https://crking92.github.io/Hays-Botany-Public/. The original https://crking92.github.io/Hays-County-Botany/ website remains the public fallback and its historic plant library/manifest remain **READ-ONLY for future botanical edits**. No canonical homepage/site takeover was approved.

## Current operational footprint

- **1,191 existing species, 146 families, 10 destination collections.** The public hub index preserves stable IDs and original source paths.
- **Nine non-grass photo-backed family sites** serve their own verified lesson pages and 723 photo references (721 GitHub-hosted, two remotely linked licensed Commons originals).
- **Poaceae** has its own photo-backed review learner but default grass species results still open the historic original learner. This is a deliberate routing hold, not a missing transfer.
- All eight grouped collections have complete original-source preservation (4,982 files across 899 species), separate from the earlier specialist Poaceae and Asteraceae transfers.
- Hub search has 1,143 nonempty common names imported from its ten public family indexes. Another 18 records lack scientific display-name metadata; their original searchable slug-based labels remain. No new taxon was invented or installed by this enrichment.
- Live Chromium interaction QA passed at 320, 390, 768 and 1280px, including common-name search, scientific-name search, family filtering, browser Back, exact species deep links and no horizontal document overflow. [Browser test evidence](https://github.com/Crking92/Hays-Botany-Public/actions/runs/41085939694).
- The full nine-family hosted-photo load/decode test passed for all 721 images: [existing gallery verification](https://github.com/Crking92/Hays-Botany-Public/actions/runs/41082428815).
- The family intake preflight checks all 146 assigned families and each of the 10 live destination branch refs without writing any taxon or website bytes: [intake preflight](https://github.com/Crking92/Hays-Botany-Public/actions/runs/41086145695).

## Species navigation contract

The hub's `data/collections.json` is the explicit **public family-link allowlist**, not scientific source ownership. Search results for nine verified non-grass collections open `https://crking92.github.io/Hays-Botany-<Collection>/site/?species=<stable-id>`; Poaceae results open `https://crking92.github.io/Hays-County-Botany/?species=<stable-id>` until separately approved otherwise. This is tested and reversible. Family buttons narrow the hub search; query strings `?species=<id>`, `?family=<family>` and `?q=<search>` are shareable hub search states. No photo image bytes are copied into the public hub.

## New-data contract

The active family edit route is https://github.com/Crking92/Hays-County-Botany/blob/main/workflow/ACTIVE_NEW_PLANT_WRITE_ROUTING_20261028.json. **Future species data, photo records, diagnostic anatomy, genus/family lessons, and local indexes belong only in their assigned Hays-Botany family source branch**; the old hub is not an editor. Validate current target branch and exact blob, claims, licensed media provenance, taxonomic identity and Hays/BONAP context before writing.

- Stage **text/scientific edits** to the assigned family source branch; the existing legacy-hub text ZIP importer is a safe route planner and refuses overwriting different cards. New photos require their own creator, exact source, license/permission, hash, crop/annotation and attribution review. This is a public Git history; never add unknown/private-only third-party source media.
- A family staging commit does **not** update the family learner on main or the central hub automatically. Reviewed publication to `main/site`, visual/mobile verification and the hub catalog refresh are distinct release steps.
- `scripts/refresh_family_search_metadata.py` reads family **public main** indexes and updates the 1,191 existing IDs without changing source paths or creating new plants; it intentionally refuses silent additions until a separately reviewed new-species search-index expansion is implemented.
- The original learner fallback remains intact, prior scheduled automations remain paused, and no uncontrolled reverse sync or cutover is enabled.

[New-data intake handoff and family branch examples](NEW_DATA_INTAKE_READY_20261030.md) · [Verified grouped-source status](https://github.com/Crking92/Hays-Botany-Lamiales/blob/main/migration/CROSS_COLLECTION_SOURCE_TRANSFER_STATUS_20261030.md)

## QA / rollback

The public hub's independent `.github/workflows/validate-hub.yml` verifies source counts and URL allowlists; `test-hub-mobile-navigation.yml` tests browser search and layout; `verify-new-data-routes.yml` checks destination branches; `verify-live-photo-galleries.yml` verifies gallery images; the historic original site remains available if any new family website is temporarily unavailable. A successful GitHub commit is never, by itself, proof that source data is released or deployed.

**Historic superseded note:** the October 28 starter description of all collections as NOT_LIVE and public hub Pages as disabled is no longer current. Public visibility of staging/hold photo history remains a rights concern separate from filtered Pages publishing. No visibility changes or history rewrites are authorized by this contract.
