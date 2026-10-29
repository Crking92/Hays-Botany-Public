#!/usr/bin/env python3
"""Fail-closed validation for the un-deployed Hays Botany hub preview."""
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
    insist(hub.get("status") == "PLANNED_ONLY_NO_LIVE_FAMILY_ROUTING", "no production routing allowed")
    insist(index.get("canonical_source_repository") == "Crking92/Hays-County-Botany", "canonical source must stay original")
    insist(index.get("source_manifest_blob_sha") and len(index["source_manifest_blob_sha"]) == 40, "pinned source blob sha required")
    insist(len(species) == index.get("source_count") == 1191, "unexpected source species count")
    insist(len(families) == 146, "unexpected family count")
    insist(len(collections) == 10, "expected ten collections")
    insist(all(c.get("live_url") is None for c in collections), "do not mark family sites live without verified cutover")
    insist(all("NOT_LIVE" in c.get("status", "") for c in collections), "every family collection remains unpublished")
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
    insist("PLANNED_ONLY_NO_LIVE_FAMILY_ROUTING" in script and "?species=" in script, "hub must keep strict original-site fallback")
    if errors:
        print("\n".join("ERROR: " + s for s in errors))
        return 1
    print(f"PASS: {len(species)} species / {len(families)} families / {len(collections)} staging collections.")
    print("PASS: no duplicate IDs or missing family assignments; all family sites remain non-live.")
    print("PASS: original authoritative learner preserved; static hub asset references present.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
