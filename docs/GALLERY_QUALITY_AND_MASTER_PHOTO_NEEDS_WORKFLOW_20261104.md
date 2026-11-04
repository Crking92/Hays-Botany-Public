# Hays Botany — active gallery-quality and master photo-needs workflow

**Effective:** 2026-11-04. **Owner approved:** gallery improvement alongside a single cross-family list of specific photo needs, without a general new-download campaign yet.

## Authoritative sources and routing

- Species identification, taxon treatment, per-photo credits, exact license, media SHA/source URL, photo roles, public gallery record and published website: **the current family GitHub repository's `main` branch** and actual family Pages site. The historical `staging/original-source-transfer` branches remain preserved.
- Family ownership: the existing active registry in `Crking92/Hays-County-Botany/workflow/ACTIVE_NEW_PLANT_WRITE_ROUTING_20261028.json`, **read-only**. New botanical or image writes must NEVER go into the legacy `Crking92/Hays-County-Botany` repository.
- Cross-family **photo needs/planning**: existing native Google Sheet `Hays_Botany_ID_Master_Curation_Tracker`, tab `Photo Needs Queue`; file ID `15dcpbk3msvOiGtAo2GRQkCfdhBR9iav-yQ0HoTjS6wM`, 14 pre-existing columns. **One master queue only**: no per-family spreadsheets, no separate replacement photo trackers.
- The historical recovery project is closed to new active work. `data/exports/historical_photo_recovery_retired_20261104.json` preserves the honest 206 unmatched snapshot (nine previously excluded). Old originals/metadata/rights remain intact and unpublished unless already positively verified and approved separately. Do not reopen recovery or manufacture zero unmatched by rewriting the audit.

## Routine cycle while refining photos

1. Read the assigned family repository card/gallery and its latest public website, plus any existing queue targets. Confirm source, species name, observed role, photo originality/credit and whether the photo actually renders in the public learner.
2. Review actual images, not file names alone. Inventory recognizable **whole-plant habit, foliage, stems, flower, fruit/seed, seasonal variation**. Some species legitimately lack ordinary showy flowers or fruit photos; use biology-specific labels.
3. Add family/genus-specific diagnostic requirements where they help identify the species, including practical look-alikes. Examples: Poaceae ligule/collar, rooted base, panicle, spikelet, glumes/lemma/awn; Cyperaceae triangular vs rounded culm, sheath, achene and perigynium where applicable; Asteraceae involucre/phyllaries, disk and ray florets, pappus/achenes; Fabaceae stipules, leaflet arrangement, inflorescence, pod; Euphorbiaceae cyathium/glands/capsule; Vitaceae mature leaf, tendril/node/adhesive disk, berries; oaks buds/bark/acorns.
4. **Before calling a photo missing**, check live family media and any already-cleared pending gallery images. Use statuses: `Confirmed absent`, `Present but inadequate`, `Present — adequate`, `Not reviewed`, or `Candidate exists — identity/rights pending`. Do not treat missing role metadata as evidence that a structure is absent.
5. Search the EXISTING master `Photo Needs Queue` by **Species ID + Exact photo target**, update a matching row if one exists, append only when target genuinely new. Preserve its original 14 columns and existing rows. `Existing source evidence` should cite the actual inspected family gallery media or source photo IDs; `Requested camera view / scale` must make collection/download actionable.
6. `New download?` must distinguish `No — covered`, `No — source candidate pending verification`, `Not yet — inspect existing gallery`, and `Later — focused download needed`. Request **later focused download** only for confirmed missing or inadequate high-value structures; no automatic mass downloads until the owner requests the next collection batch.
7. Rank priorities by crew field-ID value, not number of photos. Prioritize critical ID cues and seasonality over decorative variety. Include genus-level look-alike contrasts, especially where reproductive parts distinguish species.
8. Improvement of existing published media: correct identities and licenses when evidence warrants, prefer complementary angles over duplicates, and improve first-photo order. Publish only genuinely reviewed safe changes through the assigned family repository, validate and verify the **public website**, not merely the commit.
9. Keep site attribution and photo-specific rights (CC0, CC BY, CC BY-SA, conditional NC on genuinely noncommercial use, or exact owner-display permission) in GitHub. Do not relabel private-study or all-rights-reserved photos as CC.
10. BONAP/NAPA county distributions guide native/local priority for Hays and the established nearby western/northern target counties. Do not infer Hays nativity from Texas-wide status.

## Queue column contract (existing 14-column sheet)

`Family`, `Genus`, `Scientific name`, `Species ID`, `Exact photo target`, `Requested camera view / scale`, `Evidence status`, `Existing source evidence`, `Priority`, `Next action`, `New download?`, `Rights/identity gate`, `Destination repository`, `Last reviewed`.

A high-quality record is **one needed camera view**, not a generic request like "more species photos"; identical taxon+target rows should be updated rather than duplicated. The sheet is a working projection/coordination surface, not the authority for published-photo status. Exact species gallery and credits stay in GitHub.

## Responsibility and reporting

Five existing gallery-quality automations cover **all ten family collection repositories**: Asterids & Allies + dedicated Asteraceae; Spurges & Mallows + dedicated Fabaceae; Lamiales & Mixed Families; Monocots & Aquatics + Trees & Shrubs + dedicated Poaceae; and Cacti & Buttercups + cross-collection read-only QA. Each worker writes only its explicitly assigned repositories, reviews one repository at a time, and uses the same Photo Needs Queue. Do not assume a repository is already audited merely because it has been assigned.

Each run should report: species visually reviewed, genuinely useful site corrections **verified live**, existing photographic structures found, exact queue targets updated/added, unresolved source/ID holds, and future download targets by family/genus. A missing role may remain pending rather than inventing coverage or missing structure. Only make Sheets changes after checking the specific row against current GitHub and existing queue state; preserve all other tracker tabs and formulas.

**Progress is measured in properly attributed photos visible on family websites and identification gaps accurately resolved, not downloaded or staged files.**
