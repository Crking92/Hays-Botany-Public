#!/usr/bin/env python3
"""Refresh one-photo, zero-photo and all-photo count CSVs from public family site indexes."""
import argparse,csv,concurrent.futures as cf,json,re,time,urllib.request,urllib.error,urllib.parse
from datetime import datetime,timezone
from pathlib import Path
NAMES=["Fabaceae","Asteraceae","Monocots-Aquatics","Lamiales","Asterid-Allies","Cacti-Buttercups","Spurges-Mallows","Trees-Shrubs","Mixed-Families","Poaceae"]
BASE=[91,180,113,102,118,107,130,133,105,112]
FIELDS=["collection","family","genus","scientific_name","common_name","species_id","published_photo_count","photo_count_basis","collector_query","family_learner_url","github_repository","bonap_local_native_status"]
def fetch(repo,path):
    u="https://raw.githubusercontent.com/Crking92/Hays-Botany-"+repo+"/main/"+path
    e=None
    for k in range(4):
        try:
            q=urllib.request.Request(u,headers={"User-Agent":"HaysBotanyPublishedPhotoBackfill/1.0"})
            with urllib.request.urlopen(q,timeout=35) as r:
                if r.status!=200:raise RuntimeError("Non-200 "+u)
                return json.load(r)
        except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as x:
            e=x
            if k<3:time.sleep(k+1)
    raise RuntimeError("Cannot verify "+u+": "+str(e))
def make(repo,r,count,basis):
    sid=r["id"];s=(r.get("scientific_name") or r.get("scientific") or "").strip()
    common=(r.get("common_name") or r.get("common") or "").strip()
    genus=(r.get("genus") or s.split(" ")[0]).strip()
    family="Poaceae" if repo=="Poaceae" else r["family"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",sid) or not genus or not family:
        raise RuntimeError("Invalid scientific identity in "+repo+"/"+sid)
    return dict(collection="Hays-Botany-"+repo,family=family,genus=genus,scientific_name=s,
      common_name=common,species_id=sid,published_photo_count=count,photo_count_basis=basis,
      collector_query=s or (genus+" "+sid.removeprefix(genus.lower()+"-").replace("-"," ")),family_learner_url="https://crking92.github.io/Hays-Botany-"+repo+"/site/?species="+sid,
      github_repository="https://github.com/Crking92/Hays-Botany-"+repo,
      bonap_local_native_status=("NOT_CHECKED_IN_THIS_EXPORT" if s else "SCIENTIFIC_NAME_ABSENT_USE_PROVISIONAL_SEARCH_QUERY"))
def collect(n):
    base=BASE[NAMES.index(n)]
    if n=="Poaceae":
        idx=fetch(n,"site/data/poaceae-index.json")
        if isinstance(idx,dict):idx=idx["entries"]
        gallery=fetch(n,"site/data/gallery-index.json")
        if len(idx)<base or gallery["species"]!=len(idx):raise RuntimeError("Poaceae baseline mismatch")
        if set(gallery["entries"])!={x["id"] for x in idx}:raise RuntimeError("Poaceae gallery ID mismatch")
        def one(r):
            sid=r["id"];card=fetch(n,"site/data/species/"+sid+".json")
            panels=card.get("panels",[])
            if card["id"]!=sid or len(panels)!=gallery["entries"][sid]["count"]:
                raise RuntimeError("Poaceae species-panel mismatch "+sid)
            unique={p.get("src") for p in panels if p.get("src") and
                 p.get("photo_role")!="COMPARISON_SPECIES_SOURCE" and p.get("source_species_id",sid)==sid}
            return make(n,r,len(unique),"DISTINCT_TARGET_SPECIES_IMAGES_NOT_PANELS")
        with cf.ThreadPoolExecutor(max_workers=10) as ex:return list(ex.map(one,idx))
    idx=fetch(n,"site/data/collection-index.json")["entries"]
    if len(idx)<base:raise RuntimeError(n+" index truncated")
    if n=="Lamiales":
        m=fetch(n,"site/data/reviewed-external-photo-manifest.json")["species"]
        if not set(m).issubset({x["id"] for x in idx}):raise RuntimeError("Lamiales photo link/species mismatch")
        return [make(n,r,len({p["src"] for p in m.get(r["id"],[])}),"PUBLISHED_HOSTED_OR_LINKED_IMAGES") for r in idx]
    g=fetch(n,"site/data/gallery-index.json")
    if g["species"]!=len(idx) or set(g["entries"])!={r["id"] for r in idx}:
        raise RuntimeError(n+" gallery index conflict")
    if any(not isinstance(r.get("photo_count"),int) or g["entries"][r["id"]]["count"]!=r["photo_count"] for r in idx):
        raise RuntimeError(n+" species photo counts incorrect")
    if sum(r["photo_count"] for r in idx)!=g["photo_count"]:
        raise RuntimeError(n+" published gallery total mismatch")
    return [make(n,r,r["photo_count"],"PUBLISHED_SPECIES_PHOTOS") for r in idx]
def write_csv(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("data/exports"))
    args=ap.parse_args()
    out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futures={n:ex.submit(collect,n) for n in NAMES}
        groups={n:futures[n].result() for n in NAMES}
    rows=[r for n in NAMES for r in groups[n]]
    if len(rows)!=len({(r["family"],r["species_id"]) for r in rows}):
        raise RuntimeError("Duplicated species IDs")
    order=lambda r:(r["collection"].lower(),r["family"].lower(),r["scientific_name"].lower())
    one=sorted([r for r in rows if r["published_photo_count"]==1],key=order)
    zero=sorted([r for r in rows if r["published_photo_count"]==0],key=order)
    for name,data in [("one_photo_species.csv",one),("zero_photo_species.csv",zero),
                      ("all_species_photo_counts.csv",sorted(rows,key=order))]:
        write_csv(out/name,data)
    summary={"snapshot_utc":datetime.now(timezone.utc).isoformat(),
      "species_total":len(rows),"one_photo_species_total":len(one),"zero_photo_species_total":len(zero),
      "scope":"Published website photo sources only, not historical holds",
      "grass_counting":"Distinct own-species photo file references, not teaching panels or comparison photos",
      "native_range_note":"BONAP NAPA Hays County native status not checked; include exotics",
      "collections":{"Hays-Botany-"+n:{"species":len(groups[n]),
       "one_photo":sum(r["published_photo_count"]==1 for r in groups[n]),
       "zero_photo":sum(r["published_photo_count"]==0 for r in groups[n]),
       "two_or_more":sum(r["published_photo_count"]>=2 for r in groups[n])} for n in NAMES}}
    (out/"photo_count_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
