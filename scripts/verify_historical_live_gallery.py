#!/usr/bin/env python3
"""Read-only verify historical source photos actually visible on public family Pages.
Verify exact original bytes plus creator/source/license on LIVE species JSON. 
A verified GitHub commit alone is not a successful public-image installation.
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

REPORTS=[
 "multi-family-historical-archive-trust-2026-11-03.json",
 "multi-family-historical-ported-cc-2026-11-03.json",
 "multi-family-historical-public-domain-2026-11-03.json",
 "multi-family-historical-kew-synonyms-2026-11-03.json",
 "multi-family-historical-redirect-fix-2026-11-03.json",
 "multi-family-historical-unindexed-inat-2026-11-03.json",
 "multi-family-historical-inat-taxon-photos-2026-11-03.json",
 "multi-family-historical-card-inat-2026-11-03.json",
 "multi-family-historical-card-commons-2026-11-03.json",
 "multi-family-historical-cc-url-resolved-2026-11-03.json",
 "multi-family-historical-kew-followup-2026-11-03.json",
 "multi-family-historical-kew-followup-b-2026-11-03.json",
 "multi-family-historical-named-cc0-2026-11-03.json",
 "multi-family-historical-plantnet-licensed-2026-11-03.json",
 "multi-family-species-card-reconciliation-2026-11-03.json",
 "multi-family-commons-direct-cc-recovery-2026-11-03.json",
]
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"HaysBotanyPhotoAudit/1.1"})
    with urllib.request.urlopen(req,timeout=28) as response:
        if response.status!=200:raise RuntimeError("HTTP "+str(response.status))
        return response.read()

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repository",required=True)
    a.add_argument("--site-root",default="site")
    args=a.parse_args()
    repo=args.repository
    if not repo.startswith("Crking92/Hays-Botany-"):raise RuntimeError("Wrong family repository")
    base="https://crking92.github.io/"+repo.split("/",1)[1]+"/site/"
    site=Path(args.site_root)
    selected={}
    by_report={}
    for name in REPORTS:
        p=site.parent/"workflow"/name
        if not p.is_file():continue
        report=json.loads(p.read_text())
        rows=[]
        for b in (report.get("previous_batches") or [])+[report]:
            rows.extend(b.get("records") or [])
        count=0
        for r in rows:
            if r.get("status")!="SOURCE_VERIFIED_READY":continue
            src=r.get("src")
            if not src or not src.startswith("media/"):continue
            if not r.get("sha256") or not r.get("creator") or not r.get("source_page"):
                raise AssertionError("Incomplete individual approval record "+repr(r)[:100])
            sid=r["species_id"]
            f=site/src
            if not f.is_file():
                raise AssertionError("Published historical source media missing "+src)
            if hashlib.sha256(f.read_bytes()).hexdigest()!=r["sha256"]:
                raise AssertionError("Archived media checksum drift "+src)
            card=json.loads((site/"data/species"/(sid+".json")).read_text())
            matched=any(p.get("src")==src and p.get("creator")==r.get("creator")
                and p.get("license")==r.get("license")
                and p.get("source_page")==r.get("source_page")
                for p in card.get("verified_photos",[]))
            if not matched:raise AssertionError("Local gallery credit mismatch "+src)
            selected[src]=r
            count+=1
        by_report[name]=count
    print("HAYS_HISTORICAL_GITHUB_INSTALLED",len(selected),
        "REPORT_COUNTS",json.dumps(by_report),flush=True)
    if not selected:return
    pending=dict(selected)
    verified={}
    for attempt in range(78):
        for src,r in list(pending.items()):
            try:
                published=fetch(base+src)
                if hashlib.sha256(published).hexdigest()!=r["sha256"]:
                    raise AssertionError("Published media SHA differs "+src)
                sid=r["species_id"]
                public_card=json.loads(fetch(base+"data/species/"+sid+".json"))
                if not any(p.get("src")==src and p.get("creator")==r["creator"] and
                           p.get("source_page")==r["source_page"] and
                           p.get("license")==r["license"]
                           for p in public_card.get("verified_photos",[])):
                    raise AssertionError("Public gallery credit missing "+src)
                verified[src]=sid
                pending.pop(src)
            except (urllib.error.URLError,AssertionError,TimeoutError,ValueError) as e:
                if attempt in (0,5,12):
                    print("PUBLIC_PHOTO_RECHECK",src,str(e)[:125],flush=True)
        print("PUBLIC_PHOTO_PROGRESS",len(verified),"/",len(selected),"remaining",len(pending),flush=True)
        if not pending:break
        time.sleep(8)
    print("HAYS_HISTORICAL_SITE_PHOTOS_LIVE",len(verified),
          "SPECIES",len(set(verified.values())),"LEFT",len(pending),flush=True)
    if pending:raise AssertionError("Not all archived photos live on Pages: "+
        repr(sorted(pending.keys())[:12]))

if __name__=="__main__":main()
