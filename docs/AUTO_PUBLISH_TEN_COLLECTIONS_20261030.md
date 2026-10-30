# Hays Botany — ten-collection automated photo-publishing rollout

**Status October 30, 2026:** The 10 family repositories now each have an approved-photo intake workflow, target-site publisher and an isolated passing test. Existing source photos, lesson text, credits and annotated arrows remain unchanged by installing this system. This is a capability rollout, **not proof that a first new photo has been sent through the production event**. Some expanded post-rollout GitHub Action QA jobs are queued; do not claim they succeeded until their runs complete.

## How the flow operates

Send a photo and its exact approved metadata record to `photo-intake/approved/<species-id>/<photo-name>.jpg` and `<photo-name>.jpg.json` on the **assigned family source branch**. On push, its branch-based GitHub Actions workflow checks real media bytes (JPG/PNG/WEBP, max 25MB), species ID, exact photographer and source, license URL, review/approval metadata, duplicates and path conflicts. It then edits an isolated worktree for the corresponding published `main/site` files. The release commits only website gallery files and requests GitHub Pages build.

**The image has to be legitimately reusable before uploading to PUBLIC GitHub history.** The current pipeline does not recognize rights from pixels or invent owner permission. It requires verifiable source/rights metadata. Taxon ID, role and anatomy arrow claims are not independently confirmed by a GitHub CI script. Corrections through the learner are welcome, but correcting a public website later cannot retroactively authorize an unauthorized image in Git history.

## Assignment and branch table

| Collection | Source upload branch | Gallery representation | Photo workflow |
| --- | --- | --- | --- |
| Fabaceae | `staging/fabaceae-metadata` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Fabaceae/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Asteraceae | `staging/asteraceae-metadata` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Asteraceae/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Monocots & Aquatics | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Monocots-Aquatics/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Lamiales | `staging/original-source-transfer` | Existing reviewed photo manifest and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Lamiales/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Asterid Allies | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Asterid-Allies/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Cacti & Buttercups | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Cacti-Buttercups/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Spurges & Mallows | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Spurges-Mallows/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Trees & Shrubs | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Trees-Shrubs/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Mixed Families | `staging/original-source-transfer` | Species gallery and counters | [Workflow](https://github.com/Crking92/Hays-Botany-Mixed-Families/blob/main/.github/workflows/auto-publish-approved-photos.yml) |
| Poaceae | `main` | New credited source photo anatomy panel; existing arrows untouched | [Workflow](https://github.com/Crking92/Hays-Botany-Poaceae/blob/main/.github/workflows/auto-publish-approved-photos.yml) |

## Species source data

The source-to-site updater is currently **piloted in Asterid Allies**. Its `scripts/sync_source_species_to_site.py` inspects only changed source `species.json` files, adds new family-indexed species or updates existing lessons while preserving approved photos and existing diagnostic content when an incoming source omits it. It marks automatically imported records as reviewable; it does not independently certify the plant's taxonomy, BONAP nativity, or any anatomy arrows. [Source-sync workflow](https://github.com/Crking92/Hays-Botany-Asterid-Allies/blob/main/.github/workflows/auto-sync-source-species.yml). **This is not yet deployed across all ten collections.**

The [central family hub](https://crking92.github.io/Hays-Botany-Public/) also checks the nine published non-grass family indexes on page load, adding newly released species to its temporary in-browser search without overwriting the original 1,191-record historical snapshot. New grass IDs are not auto-added to the hub yet because Poaceae still uses original-learner fallback routing.

## What happens when user reports wrong information

1. Locate the species via stable ID, family-to-repo registry and current branch/head.
2. Correct the source species record, or remove/replace the actual approved photo/caption only after checking current site media references. Photo additions are append-only; corrections require a separate targeted edit.
3. Check the public species page and credits following release; never replace source photos or alter original hub science automatically.
4. If taxonomy or BONAP Hays target-range evidence is uncertain, state that as uncertainty and keep the plant's native-range designation separate from a lesson's provisional import status.

## QA and remaining work

- All 10 isolated approved-photo intake tests had passed at time of this rollout. No uploaded real new image has been published by the new workflow yet.
- A growing-gallery verifier was installed for the five new grouped-family pipelines because the old migration-only QA expected fixed photo counts. Its latest post-install runs were **queued** at report writing; do not misreport them as passed.
- Lamiales' manifest-specific and Poaceae's panel-specific isolated publisher tests passed.
- Full hands-off **new species** acceptance, metadata extraction from arbitrary images, and automatic diagnostic arrows **are not finished**; those require source-grounded taxonomic evidence and image-location verification. The user approved feedback-based editorial correction, not fictional attributions, source claims or permission.
- Existing original website and old scheduled workers remain unchanged/paused.
