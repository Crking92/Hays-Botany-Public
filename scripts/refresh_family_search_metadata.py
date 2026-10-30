#!/usr/bin/env python3
"""Refresh search-only names from existing published family indexes.

Does NOT install a taxon, alter botanical source paths, publish images or change
family routes. Exactly the same 1,191 hub species must be matched by ID+family.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data/species-index.json"
COLLECTIONS=ROOT/"data/collections.json"
OWNER="Crking92"

def remote_json(url):
    error=None
    for attempt in range(4):
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"HaysBotanyHubMetadataAudit/1.0"})
            with urllib.request.urlopen(request,timeout=30) as response:
                if response.status!=200:raise RuntimeError(f"HTTP {response.status}: {url}")
                return json.load(response)
        except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as exc:
            error=exc
            if attempt<3: time.sleep(2*(attempt+1))
    raise RuntimeError(f"Family index unavailable: {url}: {error}")

def collect(hub):
    destination={}
    counts={}
    for group in hub["collections"]:
        repo=group["id"]
        if repo=="Hays-Botany-Poaceae":
            rel="site/data/poaceae-index.json"
        else:
            rel="site/data/collection-index.json"
        url=f"https://raw.githubusercontent.com/{OWNER}/{repo}/main/{rel}"
        obj=remote_json(url)
        rows=obj if isinstance(obj,list) else obj.get("entries")
        if not isinstance(rows,list) or len(rows)!=group["installed_species_baseline"]:
            raise RuntimeError(f"Unexpected family inventory length for {repo}")
        for row in rows:
            sid=row.get("id")
            fam=row.get("family") or ("Poaceae" if repo=="Hays-Botany-Poaceae" else None)
            if not sid or fam not in group["families"]:
                raise RuntimeError(f"{repo}: unknown species/family: {sid} / {fam}")
            key=(sid,fam)
            if key in destination:
                raise RuntimeError(f"Duplicate family species: {key}")
            sci=(row.get("scientific_name") or row.get("scientific") or "").strip()
            common=(row.get("common_name") or row.get("common") or "").strip()
            # Some inherited species lessons lack a scientific-name display field.\n            # Preserve the stable-ID search label rather than inventing a name.
            if common.lower()==sci.lower():common=""
            destination[key]=(sci,common,repo)
        counts[repo]=len(rows)
    return destination,counts

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true",help="Update search metadata in hub index only")
    args=ap.parse_args()
    index=json.loads(INDEX.read_text())
    hub=json.loads(COLLECTIONS.read_text())
    records=index["records"]
    if index["source_count"]!=1191 or len(records)!=1191 or len(hub["collections"])!=10:
        raise RuntimeError("Hub source snapshot changed; manual review required")
    resolved,counts=collect(hub)
    source_keys={(row["id"],row["family"]) for row in records}
    if len(source_keys)!=len(records) or source_keys!=set(resolved):
        missing=sorted(source_keys-set(resolved))
        unexpected=sorted(set(resolved)-source_keys)
        raise RuntimeError(f"Family source/index mismatch. Missing {len(missing)}: {missing[:12]}; extra {len(unexpected)}: {unexpected[:12]}")
    updated=0
    common_total=0
    for row in records:
        sci,common,repo=resolved[(row["id"],row["family"])]
        before=(row.get("scientific_name"),row.get("common_name"),row.get("metadata_source"))
        after=(sci,common,f"{repo}:main")
        if before!=after:updated+=1
        row["scientific_name"]=sci
        row["common_name"]=common
        row["metadata_source"]=f"{repo}:main"
        if common:common_total+=1
    # Do not change stable IDs, taxon source paths, family routes, or authority flags.
    report={"result":"PASS_EXISTING_ONLY","species":len(records),
            "source_repository":index["canonical_source_repository"],
            "with_common_name":common_total,"metadata_changes":updated,
            "family_collection_counts":counts,"mode":"APPLY" if args.apply else "DRY_RUN"}
    if args.apply and updated:
        INDEX.write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
