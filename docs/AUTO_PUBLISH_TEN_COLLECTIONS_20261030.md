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

The source-to-site updater is now **installed in all ten family collections**, using the assigned botanical source branch in each one. For the nine non-grass collections, `scripts/sync_source_species_to_site.py` inspects only changed `content/taxa/**/species.json` files, adds new family-indexed species or updates existing lesson text without deleting approved gallery media. The dedicated Poaceae `scripts/sync_grass_source_species.py` adapter retains established anatomical panels, arrows and steps while adding provisional text-only new grass lessons. Both mark automatic imports as reviewable and do not independently certify taxonomy, BONAP range or visible anatomy. [Non-grass source-sync example](https://github.com/Crking92/Hays-Botany-Asterid-Allies/blob/main/.github/workflows/auto-sync-source-species.yml) · [Poaceae source-sync workflow](https://github.com/Crking92/Hays-Botany-Poaceae/blob/main/.github/workflows/auto-sync-grass-source.yml). **These source-sync release paths have not yet passed their newly queued GitHub Actions test runs and have not processed a real species-change event.**

The [central family hub](https://crking92.github.io/Hays-Botany-Public/) now checks the nine published non-grass family indexes **and the dedicated Poaceae review index** on page load, adding newly published species to its in-browser search without overwriting the original 1,191-record snapshot. Existing grass IDs still open the original fallback; only genuinely new grass IDs can open the dedicated Poaceae site.

## What happens when user reports wrong information

1. Locate the species via stable ID, family-to-repo registry and current branch/head.
2. Correct the source species record, or remove/replace the actual approved photo/caption only after checking current site media references. Photo additions are append-only; corrections require a separate targeted edit.
3. Check the public species page and credits following release; never replace source photos or alter original hub science automatically.
4. If taxonomy or BONAP Hays target-range evidence is uncertain, state that as uncertainty and keep the plant's native-range designation separate from a lesson's provisional import status.

## QA and remaining work

- All 10 isolated approved-photo intake tests had passed at time of this rollout. No uploaded real new image has been published by the new workflow yet.
- A growing-gallery verifier was installed for the five new grouped-family pipelines because the old migration-only QA expected fixed photo counts. Its latest post-install runs were **queued** at report writing; do not misreport them as passed.
- Lamiales' manifest-specific and Poaceae's panel-specific isolated publisher tests passed.
- Automatic new-species **source-to-site code and branch triggers are installed in all ten repositories**, but their most recent CI integration runs are queued, so the end-to-end source-release automation is NOT yet verified in production. Automatic interpretation of arbitrary photographs, independent license/identity proof, reliable anatomy arrows, and a completely zero-metadata upload experience remain unfinished; these require source-grounded taxonomic evidence and image-location verification. The user approved feedback-based editorial correction, not fictional attributions, source claims or permission.
- Existing original website and old scheduled workers remain unchanged/paused.
