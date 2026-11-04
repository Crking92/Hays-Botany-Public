#!/usr/bin/env python3
"""Retry only archived iNaturalist photos explicitly CC0 and individually named.
Exact live photo-level CC0 code, original photo and observation IDs, source
taxon, original SHA and matching pixels are mandatory. Generic/unknown authors
remain held. The archived named photographer is preserved when iNaturalist's
current attribution says only 'no rights reserved'.
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(a,b,count=1):
 global s
 if s.count(a)!=count:raise RuntimeError("Unexpected source-auditor revision: "+a[:55])
 s=s.replace(a,b,count)
change('''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}''',
'''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="inat" and
       str(r.get("reason","")).startswith(
         "Current photo creator differs from original image CSV: no rights reserved")}''')
change('def inat_verify(c:dict)->dict:', '''def inat_verify(c:dict)->dict:
    name=creator_display(c.get("claimed_creator"))
    if not str(c.get("claimed_license") or "").upper().startswith("CC0"):
        raise RuntimeError("Original individual license does not say CC0")
    if not name or any(t in name.casefold() for t in
      ("unknown","anonymous","unverified","photographer","contributor",
       "no rights reserved","source account","inaturalist photo")):
        raise RuntimeError("No individually named original photo creator; stay held")
    obs_id=int(c["observation_id"]);pid=int(c["photo_id"])
    response=request("https://api.inaturalist.org/v1/observations/"+str(obs_id),json_response=True)
    rows=response.get("results") or []
    if len(rows)!=1 or rows[0].get("id")!=obs_id:
        raise RuntimeError("Exact originally recorded observation not found")
    obs=rows[0];taxon=str((obs.get("taxon") or {}).get("name") or "")
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("Original photo observation taxon mismatch: "+taxon)
    photos=[p for p in obs.get("photos") or [] if p.get("id")==pid]
    if len(photos)!=1:raise RuntimeError("Exact archived photo ID absent from observation")
    p=photos[0]
    if p.get("license_code")!="cc0":raise RuntimeError("Current individual photo rights are not CC0")
    current=str(p.get("attribution") or "").strip()
    if current.casefold()!="no rights reserved":
        raise RuntimeError("Current CC0 attribution is not the known historical generic string")
    urls=[c.get("direct_url"),c.get("direct_image_url"),p.get("large_url"),
          re.sub(r"/(?:square|medium|small|thumb)\.", "/large.",str(p.get("url") or "")),
          p.get("url")]
    distances=[]
    for u in dict.fromkeys(str(x) for x in urls if x):
        try:
            safe=collect_photo_url(u,pid)
            distance=(dhash(c["original_bytes"])^dhash(request(safe))).bit_count()
            distances.append(distance)
            if distance<=12:break
        except Exception:continue
    if not distances or min(distances)>12:
        raise RuntimeError("Preserved photo does not visually fingerprint-match its exact current ID")
    return {"license":"CC0 1.0",
      "license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
      "creator":name,"exact_page":"https://www.inaturalist.org/photos/"+str(pid),
      "taxon":taxon,"source_type":"inat-cc0","source_id":str(obs_id),
      "evidence":"Original observation "+str(obs_id)+" exact photo "+str(pid)+
        ", current individual CC0 photo-level rights, matching image fingerprint "+
        str(min(distances))+", original archived individual image-sources.csv names creator "+
        name+"; current photo attribution supplies only generic no-rights-reserved text; "+
        "historical creator was retained, not asserted as current online attribution"}
def original_inat_verify(c:dict)->dict:''')
change('multi-family-historical-archive-trust-2026-11-03.json',
       'multi-family-historical-named-cc0-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_NAMED_CC0_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_NAMED_CC0",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
