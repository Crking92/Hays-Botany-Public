> **October 29 Fabaceae archived-source recovery:** The [public Fabaceae learner](https://crking92.github.io/Hays-Botany-Fabaceae/site/) now displays **20 source-credited images across 13 of 91 species**. Two photos were recovered from already-migrated Commons/iNaturalist sources and the archive-hold folder lookup was corrected. The remaining 78 species without published photos are not missing botanical records. [Source/photo QA report](https://github.com/Crking92/Hays-Botany-Fabaceae/blob/main/migration/FABACEAE_SOURCE_AND_GALLERY_QA_CHECKPOINT_20261029.md). All nine non-grass family websites together now reference **655** released photo copies, with unchanged routing and no new media harvesting.

> **October 29 Asteraceae archived-source update:** The [live Asteraceae learner](https://crking92.github.io/Hays-Botany-Asteraceae/site/) now has **172 source-credited photos across 124/180 species**. [GitHub Actions live proof](https://github.com/Crking92/Hays-Botany-Asteraceae/actions/runs/40933112050) byte-compared all 172 publicly delivered images against their original files. **56 cards still lack a cleared gallery photo**, but their text and original archived sources remain available. Unlike Poaceae's 112/112 photo presence, Asteraceae is not photo-complete: rights holds and exact-media attribution issues are tracked, not bypassed. No new photos collected and no family routing altered.

> **POACEAE PHOTO COVERAGE COMPLETE — October 29:** All **112/112** grass species in the [dedicated Poaceae visual learner](https://crking92.github.io/Hays-Botany-Poaceae/site/) have at least one published photograph from their own source species folder, totaling **486 existing source-photo files / 604 teaching panels**. This is **photo-presence coverage**, not full anatomy-arrow/ligule QA. The source archive is preserved; 53 previously held photo originals are not automatically republished. Ten existing Bob Harms photos carry author-specific science/education-with-credit rights **not Creative Commons**, and three Larry Allain USGS photos were transferred byte-for-byte from the old repository. [Full Poaceae closeout audit](https://github.com/Crking92/Hays-Botany-Poaceae/blob/main/migration/POACEAE_FAMILY_SOURCE_PHOTO_CLOSEOUT_20261029.md). This is still an optional grass review site; default species searches stay on the original fallback until separately approved.

> **October 29 archive photo follow-up:** The optional [Poaceae review learner](https://crking92.github.io/Hays-Botany-Poaceae/site/) has **461 existing photo files, 579 panels and 103/112 grasses with target-species source-folder photos** after recovery of exact archived CC BY images for three additional grasses. Individual photo credits say the precise CC BY version was not recorded; direct original photo links remain. This is a review-site statistic update only: the original learner remains the default grass species-search destination. See the [family's rights and photo recovery evidence](https://github.com/Crking92/Hays-Botany-Poaceae/blob/main/migration/EXISTING_SOURCE_PHOTO_RECOVERY_PASS_20261029.md).

> **October 29 existing-photo recovery update:** The [separate Poaceae review learner](https://crking92.github.io/Hays-Botany-Poaceae/site/) now references **443 existing photo files across 558 teaching panels**, with **105 species showing any published picture and 100 having at least one of their own source-folder images**. The extra 74 files and 93 panels came from previously archived media; new photographs were not gathered. The other 12 species lacking target-species photos are individually tracked in [the Poaceae recovery report](https://github.com/Crking92/Hays-Botany-Poaceae/blob/main/migration/EXISTING_SOURCE_PHOTO_RECOVERY_PASS_20261029.md). Grass *species search still routes to the original learner*; the separate site is an optional review link only.

> **October 29 Poaceae review-site link update:** Poaceae now has a separately tested [live photo-backed grass learner](https://crking92.github.io/Hays-Botany-Poaceae/site/) with 112 species, 369 original source photo files and 465 visual panels. The hub's **Collections** area offers this site as an optional direct link, while its grass **species search deliberately still opens the original learner**; this is not a plant data ownership transfer, automatic source sync, or approved default species-route cutover. The existing nine family photo galleries are unchanged. More details: [grass gallery migration QA](docs/FAMILY_GALLERY_MIGRATION_QA_20261029.md).

> **Latest existing-source migration checkpoint — October 29, 2026:** This hub now routes **nine live photo-backed family learners** covering **1,079 species** (all non-grass assigned taxa) and **643 source-credited public photo references**. Of those, **641 photos are GitHub-hosted** and two Lamiales photos remain Wikimedia-linked. All nine galleries passed live HTTP image fetch and decode testing at the prior 573-photo checkpoint; the newer Lamiales/Asteraceae photo backfill is being rechecked separately. **Poaceae's 112 species** remain routed to the original learner until its dedicated Pages website is activated and verified. Family staging branches are future botanical write destinations; the original learner is read-only fallback. No new photography was collected during this migration. The earlier planning/preview descriptions below are historical and superseded where they say family websites are unpublished, private, or text-only.

# Hays Botany — Central Hub (staging preview)

**This repository is intended for the future central public hub for the Hays Botany Visual Learner. It is NOT currently the production site.**

The existing working learner and authoritative species content remain at [Hays-County-Botany](https://github.com/Crking92/Hays-County-Botany), with the live website at **https://crking92.github.io/Hays-County-Botany/**.

## What is already built here

- [Hub preview home](index.html): matches the original forest-green/cream design and offers mobile-friendly navigation.
- [Read-only species search index](data/species-index.json): **1,191 source species** with stable IDs, source paths, genera and families, pinned to original manifest blob `36c95f3d83ada2e01331b9f32ae69cb8b09c44d9`.
- [Family + collection registry](data/collections.json): **146 families in 10 planned destination repositories**, all explicitly marked as **not live**.
- Search/browse: type a scientific search label, genus, stable species ID, or family; browse family cards or inspect planned family-group repositories.
- Safe fallback: **every species result opens the existing working learner** rather than an unpublished family site. The universal Learner, Field ID, glossary and quiz still live on the original site.
- [Validation workflow](.github/workflows/validate-hub.yml) and [validator](scripts/validate_hub.py): ensure source index and planned family routing stay consistent; only read/check, never deploy.

**What this is not:** not yet a common-name-complete accepted-taxonomy catalog, not a replacement for the original learner, not a public photo archive, and not an approval to enable independent family websites. Scientific search labels are reconstructed from stable IDs for preview search only; the original source card determines accepted names and common names. No third-party photographs were migrated here.

## Preview locally (no public Pages release)

1. On GitHub, select **Code → Download ZIP** (or clone this repository).
2. Extract it; open a terminal in the repository folder.
3. Run `python -m http.server 8000`.
4. Open `http://127.0.0.1:8000/`. Do not open `index.html` directly, because browsers restrict local JSON requests.
5. Optionally run `python scripts/validate_hub.py` to verify the 1,191/146/10 source and route contract.

### Next integration stages

1. Keep the original site stable while each family staging repository completes actual media, rights and science checks.
2. Export the current accepted scientific and common names to the future hub from verified canonical species records, with SHA/freshness checks. Do not permanently rely on reconstructed labels.
3. Activate family URLs **only after each separate site is successfully published and explicitly approved**. Implement deep linking, safe original fallback, mobile tests, common glossary/quiz, and rollback.
4. Review all public repo history and every image's rights before including public photographs. Public source hosting exposes raw bytes even when Pages filters are in place.
5. Preserve one canonical species editor at a time, the original site fallback, and audit logs during transfer.

## Authoritative coordination

- [Project-wide multi-repository operating rules](https://github.com/Crking92/Hays-County-Botany/blob/main/workflow/MULTI_REPO_OPERATING_RULES_20261028.md)
- [Cross-chat handoffs](https://github.com/Crking92/Hays-County-Botany/blob/main/workflow/ACTIVE_CHAT_HANDOFFS_20261028.md)
- [This repository's AGENTS instructions](AGENTS.md)
- [Detailed preview and publishing contract](docs/INTEGRATION_CONTRACT.md)

**No public Pages deployment or original-site redirect was enabled by setting up this preview.**
