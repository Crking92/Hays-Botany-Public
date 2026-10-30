#!/usr/bin/env python3
"""Read-only new-data preflight: 146 family routes and 10 destination branches.

Source: active original hub routing registry. NO taxon or Pages edits.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY="https://raw.githubusercontent.com/Crking92/Hays-County-Botany/main/workflow/ACTIVE_NEW_PLANT_WRITE_ROUTING_20261028.json"

def get(url):
    exc=None
    for attempt in range(4):
        try:
            r=urllib.request.Request(url,headers={"User-Agent":"HaysBotanyIntakePreflight/20261030",
                                                  "Accept":"application/vnd.github+json"})
            with urllib.request.urlopen(r,timeout=20) as response:
                if response.status!=200:raise RuntimeError(f"HTTP {response.status} {url}")
                return json.load(response)
        except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as e:
            exc=e
            if attempt<3:time.sleep(2*(attempt+1))
    raise RuntimeError(f"Could not audit public route: {url}: {exc}")

def main():
    cfg=get(REGISTRY)
    hub=json.loads((ROOT/"data/collections.json").read_text(encoding="utf-8"))
    routes=cfg["family_to_repository"]
    branches=cfg["repository_write_branches"]
    assert cfg["policy"]=="ACTIVE_PROSPECTIVE_PLANT_DATA_WRITE_ROUTING"
    assert cfg["future_writes_to_original_content_taxa"] is False
    assert cfg["future_writes_to_original_data_manifest"] is False
    assert cfg["public_site_cutover_approved"] is False
    assert len(routes)==146 and len(branches)==10 and len(hub["collections"])==10
    seen={}
    for collection in hub["collections"]:
        name=collection["id"]
        assert name in branches and collection["repository"]=="Crking92/"+name
        for family in collection["families"]:
            if family in seen:raise RuntimeError("Family duplicated in hub collections: "+family)
            seen[family]=name
        branch=branches[name]
        url=f"https://api.github.com/repos/Crking92/{name}/git/ref/heads/{urllib.parse.quote(branch,safe='/')}"
        ref=get(url)
        if ref.get("ref")!="refs/heads/"+branch:
            raise RuntimeError(f"Family branch differs from active registry: {name} {branch}")
        assert ref.get("object",{}).get("sha"),"missing head SHA"
    if routes!=seen:
        missing=sorted(set(routes)-set(seen))
        wrong=sorted(f for f in routes if f in seen and routes[f]!=seen[f])
        raise RuntimeError(f"Family routing drift; missing={missing}, mismatched={wrong}")
    output={"status":"PASS_READ_ONLY_NEW_DATA_PRECHECK",
            "families":len(routes),"destinations":len(branches),
            "all_destination_branches_exist":True,
            "legacy_taxon_writes_allowed":False,"site_cutover":False,
            "new_media_imports":0,"automation_restarts":0}
    print(json.dumps(output,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
