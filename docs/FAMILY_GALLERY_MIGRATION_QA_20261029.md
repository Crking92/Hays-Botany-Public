# Hays Botany — live family galleries and migration-first QA checkpoint (2026-10-29)

Status: **READ-ONLY AUDIT**. This checkpoint does not change family routing, publish photos, collect new photos, alter botanical source, enable automations, or authorize a production-site cutover. Recheck live branches and GitHub Actions before any later edit: other chats are actively updating the collections.

## Latest verified public family-photo inventory

Read from `main` site indexes, `site/data/gallery-index.json` or Lamiales' `site/data/reviewed-external-photo-manifest.json`, and repository Git trees.

| Published family site | Species | Credited photo references | Species with published photos | Local image files |
| --- | ---: | ---: | ---: | ---: |
| Asteraceae | 180 | 162 | 116 | 162 |
| Fabaceae | 91 | 18 | 11 | 18 |
| Monocots-Aquatics | 113 | 35 | 23 | 35 |
| Lamiales | 102 | 102 | 55 | 100 (plus 2 external Commons links) |
| Asterid-Allies | 118 | 64 | 30 | 64 |
| Cacti-Buttercups | 107 | 37 | 25 | 37 |
| Spurges-Mallows | 130 | 99 | 48 | 99 |
| Trees-Shrubs | 133 | 107 | 51 | 107 |
| Mixed-Families | 105 | 19 | 14 | 19 |
| **Nine-site total** | **1,079** | **643** | **373** | **641** |

All nine repositories have nontruncated Git `main` trees, exactly the expected locally hosted site image file counts, nonzero image-byte sizes, and matching `collection-index` species-ID/gallery-index counts. For each of eight gallery-index sites, all non-null `first_src` paths were found on `main`; for Lamiales, all 100 local manifest image paths were found on `main`. No orphan species IDs or photo-count discrepancies were found. This does not alone prove every anatomical label, image identity or credit decision.

**Stronger live HTTP image-byte verification:** `Hays-Botany-Public` Actions run [40909597975](https://github.com/Crking92/Hays-Botany-Public/actions/runs/40909597975) succeeded on Oct 29 and logged `ALL_EXISTING_FAMILY_GALLERIES_LIVE_PASS`: **641 images fetched and decoded**, 2 Commons external links excluded from byte-decode test, 9 live sites, 1,079 species indexed, 0 new photos collected, original learner not modified. The central hub `main` Pages build and `validate-hub` both passed on SHA `1f200501a...` (Actions run 40909862041 and 40909864368).

Asteraceae advanced from a previous 153 images/112 photographed species to **162/116** on the live gallery index. Yarrow (`achillea-millefolium`) has 2 photo records and its gallery's two source credits. Lamiales' Monarda (`monarda-citriodora`) has restored photo entries with provenance in the reviewed-photo manifest.

## Poaceae — separately published, not yet central-hub routed

`Hays-Botany-Poaceae/site/data/poaceae-release.json` reports **112 species; 103 with visible photos; 369 physically referenced source photo files across 465 visual photo panels**. These are different units and must not be added together. The 56 deferred original Poaceae images remain preserved separately without being published into the public Poaceae repository. The old hub still routes Poaceae's 112 species to the original Hays-County-Botany learner.

The Poaceae Pages deployment succeeded on `main` SHA `04ae5484d...` in run [40911119065](https://github.com/Crking92/Hays-Botany-Poaceae/actions/runs/40911119065). An initial live Pages smoke test returned HTTP 404 *before* that deployment had finished; a subsequent rerun **passed** in [40908950876, attempt 2](https://github.com/Crking92/Hays-Botany-Poaceae/actions/runs/40908950876), logging `POACEAE_PUBLIC_PAGES_IMAGE_PASS` with 369 published photo files, 103 sampled photographed-species images successfully loaded, and 112 species. The previous 404 should not be presented as the site's current failure.

**Separate scientific/visual QA hold:** 18 Poaceae `gallery-index` entries select a `first_src` from a *different species' source directory*. Several examples are explicitly labelled LOOK-ALIKE in individual species teaching panels (e.g. `anatherum-tenuispatheum` points first to `anatherum-glomeratum`; `bromus-pubescens` points to `bromus-japonicus`; `sorghum-halepense` points to `sorghastrum-nutans`). This can be pedagogically intentional, but must not be mistaken for a verified species-identity photo. During future grass visual QA, promote true target-species photos before look-alike photos when present and ensure comparison-only pictures are visibly labelled; preserve the teaching comparisons. This is **not** evidence that 18 source files are missing, nor authority to remove those images without inspecting their role.

Earlier Poaceae dry-run and comprehensive gates are still recorded as FAILED because their hard-coded historical expected counts of 788/224 and 1178/224 no longer match the updated migration/release. Update and rerun those checks separately rather than interpreting the live Pages image smoke success as all anatomical/source-migration gates passing.

## Next safe work (existing materials first)

1. Continue source-file/reuse-status reconciliation against each assigned family staging branch and the previously recorded 7,521 original-family source files. Preserve clear distinction among **originals preserved**, **image files locally hosted**, **photos visible in galleries**, **source/rights reviewed**, **anatomy field-ready**, and **deployed**. Do not conflate 643 gallery references with all source photo files.
2. For each family, review held or excluded original images **without downloading replacements**. Keep uncertain material out of new public gallery releases; old public repository history cannot be hidden by a filtered Pages build.
3. Verify/repair outdated public-facing README/release status text that still calls these live sites private, undeployed or text-only. Use current Actions/commit SHA and do not silently alter the active botanical destination routing registry.
4. Revisit Poaceae's 18 different-source-folder first-photo entries, failing legacy count assertions, and remaining field-ID photo/arrow QA before suggesting the central hub route switch. Keep original website links as fallback.
5. No old installers or automations are to be resumed; future botanical edits go to registered family repository/branch only. Do not collect new photos, move held images to public repositories, or rewrite original source.

Compiled from the exact GitHub collection indexes, trees and successful image-delivery Actions on October 29, 2026. This is a dated audit, not an automatically updating status dashboard.
