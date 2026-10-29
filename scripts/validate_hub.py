#!/usr/bin/env python3
"""Fail-closed validation for nine verified family learner links and safe grass fallback."""
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
errors = []
def insist(ok, message):
    if not ok:
        errors.append(message)

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def main():
    index = load("data/species-index.json")
    hub = load("data/collections.json")
    species = index.get("records", [])
    families = hub.get("families", [])
    collections = hub.get("collections", [])
    insist(index.get("schema_version") == 1, "index schema version")
    insist(hub.get("schema_version") == 1, "hub schema version")
    insist(index.get("status") == "STAGING_READ_ONLY_SOURCE_SNAPSHOT", "index must remain staging only")
    insist(hub.get("status") in ("NINE_VERIFIED_FAMILY_TEXT_SITES_GRASSES_LEGACY_FALLBACK","NINE_VERIFIED_FAMILY_PHOTO_GALLERIES_GRASSES_LEGACY_FALLBACK"), "expected controlled family gallery routing")
    insist(index.get("canonical_source_repository") == "Crking92/Hays-County-Botany", "canonical source must stay original")
    insist(index.get("source_manifest_blob_sha") and len(index["source_manifest_blob_sha"]) == 40, "pinned source blob sha required")
    insist(len(species) == index.get("source_count") == 1191, "unexpected source species count")
    insist(len(families) == 146, "unexpected family count")
    insist(len(collections) == 10, "expected ten collections")
    expected_photos={
        "Hays-Botany-Asteraceae":(162,116),
        "Hays-Botany-Fabaceae":(18,11),
        "Hays-Botany-Monocots-Aquatics":(35,23),
        "Hays-Botany-Lamiales":(102,55),
        "Hays-Botany-Asterid-Allies":(64,30),
        "Hays-Botany-Cacti-Buttercups":(37,25),
        "Hays-Botany-Spurges-Mallows":(99,48),
        "Hays-Botany-Trees-Shrubs":(107,51),
        "Hays-Botany-Mixed-Families":(19,14),
    }
    live=[c for c in collections if c.get("status") in ("LIVE_TEXT_ONLY_PREVIEW","LIVE_VERIFIED_CC_GALLERY")]
    grass=[c for c in collections if c.get("id")=="Hays-Botany-Poaceae"]
    insist(len(live)==9,"nine verified family learners expected")
    insist(len(grass)==1 and grass[0].get("live_url") is None and grass[0].get("status")=="LIVE_REVIEW_ONLY_NOT_ROUTED","grass must retain original search routing until explicit cutover")
    if len(grass)==1:
        insist(grass[0].get("review_url")=="https://crking92.github.io/Hays-Botany-Poaceae/site/","grass review URL must be the tested dedicated learner")
        insist(grass[0].get("active_species_destination")=="ORIGINAL_LEGACY_LEARNER","grass search default must remain original")
        insist(grass[0].get("review_published_photo_files")==461 and grass[0].get("review_visible_photo_panels")==579,"grass review gallery inventory drift")
    for c in live:
        insist(c.get("live_url")=="https://crking92.github.io/"+c["id"]+"/site/","wrong or unverified live family URL: "+c["id"])
        if c.get("status")=="LIVE_VERIFIED_CC_GALLERY":
            photo_count,photo_species=expected_photos[c["id"]]
            insist(c.get("photos_deployed_in_this_collection")==photo_count and c.get("photographed_species")==photo_species,"family gallery count drift: "+c["id"])
        else:
            insist(c.get("photos_deployed_in_this_collection")==0,"text-only family cannot claim released photos: "+c["id"])
    if hub.get("status")=="NINE_VERIFIED_FAMILY_PHOTO_GALLERIES_GRASSES_LEGACY_FALLBACK":
        insist(all(c.get("status")=="LIVE_VERIFIED_CC_GALLERY" for c in live),"all nine photo galleries must be verified before enabling this hub status")
        insist(sum(c.get("photos_deployed_in_this_collection",0) for c in live)==643,"expected 643 existing-source cleared photo links")
    insist(sum(c["installed_species_baseline"] for c in live)==1079, "unexpected live family text-index coverage")
    insist(all(c.get("repository", "").startswith("Crking92/Hays-Botany-") for c in collections), "unexpected destination repository")
    byid = Counter(s.get("id") for s in species)
    insist(len(byid) == len(species) and all(n == 1 for n in byid.values()), "duplicate species IDs")
    family_names = {f["name"] for f in families}
    insist(len(family_names) == len(families), "duplicate family entry")
    assigned = {f for c in collections for f in c["families"]}
    insist(len(assigned) == len(family_names) and assigned == family_names, "family roster coverage")
    for f in families:
        insist(sum(f["name"] in c["families"] for c in collections) == 1, "family must have exactly one destination: " + f["name"])
        insist(sum(s["family"] == f["name"] for s in species) == f["species_count"], "source species tally mismatch: " + f["name"])
        insist(any(c["id"] == f["collection_id"] and f["name"] in c["families"] for c in collections), "wrong collection mapping: " + f["name"])
    for s in species:
        insist(s["family"] in family_names, "unrouted species: " + s["id"])
        insist(s["source_path"].endswith("/species.json"), "invalid species source path: " + s["id"])
        insist(re.fullmatch(r"[a-z0-9][a-z0-9-]*", s["id"]) is not None, "invalid species ID: " + s["id"])
    for c in collections:
        insist(c["installed_species_baseline"] == sum(f["species_count"] for f in families if f["name"] in c["families"]), "collection count mismatch: " + c["id"])
    for path in ["index.html", "assets/js/hub.js", "assets/css/hub.css", "README.md", "AGENTS.md"]:
        insist((ROOT / path).is_file(), "missing hub file " + path)
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    insist('id="searchInput"' in page and 'id="familiesGrid"' in page and 'id="collectionsGrid"' in page, "hub UI placeholders missing")
    insist("assets/js/hub.js" in page and "assets/css/hub.css" in page, "hub assets not included")
    script=(ROOT / "assets/js/hub.js").read_text(encoding="utf-8")
    insist("NINE_VERIFIED_FAMILY_TEXT_SITES_GRASSES_LEGACY_FALLBACK" in script and "familyRoute(sp)" in script and "legacyLink(sp.id)" in script, "hub must link live family text sites with original grass fallback")
    if errors:
        print("\n".join("ERROR: " + s for s in errors))
        return 1
    print(f"PASS: {len(species)} species / {len(families)} families / {len(collections)} assigned collections.")
    print("PASS: nine routed family galleries and optional live grass review link; 112 grass results retain original fallback.")
    print("PASS: original authoritative learner preserved; static hub asset references present.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
