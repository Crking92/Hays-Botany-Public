#!/usr/bin/env python3
"""Resolve archived exact photo IDs attached to iNaturalist taxon pages.
Only publish if the current taxon id, species assignment, specific photo id,
photo-level license, original photographer, and image fingerprint all match.
Never infer permission from the taxon page's general contents.
"""
from pathlib import Path
source=Path(__file__).with_name("recover_historical_archive_trust.py")
s=source.read_text()
def change(old,new,n=1):
    global s
    if s.count(old)!=n:raise RuntimeError("Photo audit changed: "+old[:70])
    s=s.replace(old,new,n)
a='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
b='''    previously_reviewed={r.get("git_blob_sha") for r in all_prior
                         if r.get("git_blob_sha")}
    eligible_held=set()'''
change(a,b)
change('''        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue''',
'''        if sh in previously_reviewed:
            omitted["already_in_original_source_review"]+=1
            continue''')
change('        card_file=src/parent/"species.json"',
'''        import re
        original_source=str(row.get("source_page") or "")
        t=re.search(r"https://www\\.inaturalist\\.org/taxa/(\\d+)",original_source)
        tid=t.group(1) if t else ""
        pid=str(row.get("photo_id") or "").strip()
        if not pid:
            u=str(row.get("direct_image_url") or row.get("direct_url") or "")
            m=re.search(r"(?:inaturalist-open-data\\.s3\\.amazonaws\\.com|static\\.inaturalist\\.org)/photos/(\\d+)/",u)
            pid=m.group(1) if m else ""
        if not (tid.isdigit() and pid.isdigit() and row.get("creator") and row.get("license")):
            omitted["not_a_photo_specific_inat_taxon_reference"]+=1;continue
        card_file=src/parent/"species.json"''')
change('''           "claimed_license":row.get("license") or "", "photo_id":row.get("photo_id") or "",
           "observation_id":row.get("observation_id") or "", "direct_url":row.get("direct_url") or "",''',
'''           "claimed_license":row.get("license") or "", "photo_id":pid,
           "taxon_id":tid,"observation_id":"", "direct_url":row.get("direct_url") or "",''')
change('        candidate["lane"]=classify(candidate)',
       '        candidate["lane"]="taxon"')
change('def classify(c:dict)->str:',
'''def taxon_photo_verify(c:dict)->dict:
    tid=int(c["taxon_id"]);pid=int(c["photo_id"])
    data=request("https://api.inaturalist.org/v1/taxa/"+str(tid),json_response=True)
    records=data.get("results") or []
    matches=[x for x in records if x.get("id")==tid]
    if len(matches)!=1:raise RuntimeError("Original taxon-page id is no longer identifiable")
    taxon=matches[0]
    taxon_name=str(taxon.get("name") or "")
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon_name==expected or taxon_name.startswith(expected+" ")):
        raise RuntimeError("Taxon-page scientific name does not match archived species: "+taxon_name)
    candidates=[x.get("photo") for x in (taxon.get("taxon_photos") or [])
                if isinstance(x,dict) and isinstance(x.get("photo"),dict)]
    default=taxon.get("default_photo")
    if isinstance(default,dict):candidates.append(default)
    photo_matches={int(p.get("id")):p for p in candidates if p.get("id")==pid}
    if pid not in photo_matches:raise RuntimeError("Exact archived photo id absent from current taxon-page photos")
    p=photo_matches[pid]
    code=p.get("license_code")
    if code not in PHOTO_CODES:raise RuntimeError("Current taxon photo individual rights unsupported: "+str(code))
    validate_claim(c.get("claimed_license"),code)
    credited=str(p.get("attribution") or "")
    if not creator_matches(c.get("claimed_creator"),credited):
        raise RuntimeError("Archived creator differs from current photo credit: "+credited[:120])
    urls=[c.get("direct_url"),c.get("direct_image_url"),p.get("large_url"),
          re.sub(r"/(?:square|medium|small|thumb)\\.", "/large.",str(p.get("url") or "")),
          p.get("url")]
    attempts=[]
    for u in dict.fromkeys(str(v) for v in urls if v):
        try:
            url=collect_photo_url(u,pid)
            difference=(dhash(c["original_bytes"])^dhash(request(url))).bit_count()
            attempts.append((difference,url))
            if difference<=12:break
        except Exception:continue
    if not attempts:raise RuntimeError("Exact taxon photo image not accessible on iNaturalist hosts")
    diff,match=min(attempts,key=lambda v:v[0])
    if diff>12:raise RuntimeError("Archived image pixels do not match taxon photo id: "+str(diff))
    return {"license":PHOTO_CODES[code][0],"license_url":PHOTO_CODES[code][1],
       "creator":creator_display(credited),
       "exact_page":"https://www.inaturalist.org/photos/"+str(pid),
       "taxon":taxon_name,"source_type":"inat-taxonomy","source_id":str(tid),
       "evidence":"Current iNaturalist taxon "+str(tid)+" exact botanical taxon "+taxon_name+
         "; individual listed taxon photo "+str(pid)+"; live photo-specific CC code "+code+
         "; photographer "+credited+"; archived source photo matched by dHash "+str(diff)+
         "; original taxon photo URL "+c.get("source_page","")}
def classify(c:dict)->str:''')
change('priority={"inat":0,"gbif":1,"commons":2}','priority={"inat":0,"gbif":1,"commons":2,"taxon":0}')
change('checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)',
       'checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify,"taxon":taxon_photo_verify}[c["lane"]](c)')
change('multi-family-historical-archive-trust-2026-11-03.json',
       'multi-family-historical-inat-taxon-photos-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_INAT_TAXON_PHOTOS_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_INAT_TAXON_PHOTOS",json.dumps({')
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
