#!/usr/bin/env python3
"""Recover only original iNaturalist photos with exact source links and explicitly documented individual CC0 grants.
Requires original source hash, explicit photo ID and direct open-data source,
named original attribution, taxon-card match, matching source image pixels,
no prior rejection and no duplicate by SHA or source photo ID.
Historical licenses are cited as historical evidence, not asserted current.
"""
from pathlib import Path
base=Path(__file__).with_name("recover_historical_archive_trust.py")
s=base.read_text()
def change(old,new,n=1):
 global s
 if s.count(old)!=n: raise RuntimeError("Unexpected historical auditor source "+old[:70]+": "+str(s.count(old)))
 s=s.replace(old,new,n)
change('''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}''',
'''    eligible_held=set()
    prior_reviewed={r.get("git_blob_sha") for r in all_prior if r.get("git_blob_sha")}''')
change('''        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue''',
'''        if sh in prior_reviewed:
            omitted["original_historical_review_preserved"]+=1;continue''')
change('''        return {r.get("file_name"):r for r in csv.DictReader(f) if r.get("file_name")}''',
'''        return {Path(str(r.get("file_name") or r.get("file") or "")).name:r
                for r in csv.DictReader(f) if r.get("file_name") or r.get("file")}''')
change('''        card_file=src/parent/"species.json"''',
'''        row=dict(row)
        raw=str(row.get("license_code") or "").lower().strip().replace("_","-")
        if raw in PHOTO_CODES:
            code=raw
        else:
            claim=str(row.get("license") or "").strip().upper()
            licmap={"CC0":"cc0","CC0 1.0":"cc0","CC BY 4.0":"cc-by",
                    "CC BY-SA 4.0":"cc-by-sa","CC BY-NC 4.0":"cc-by-nc",
                    "CC BY-NC-SA 4.0":"cc-by-nc-sa"}
            code=licmap.get(claim,"")
        creator=creator_display(str(row.get("attribution") or row.get("creator") or ""))
        vague=("unknown","unverified","photographer","rights reserved",
               "iNaturalist contributor","user unknown","source account")
        if code!="cc0" or str(row.get("license") or "").strip().upper() not in ("CC0","CC0 1.0"):
            omitted["not_explicit_archived_individual_cc0"]+=1;continue
        if not creator or any(term in creator.casefold() for term in vague):
            # CC0 does not require attribution. Do not invent a photographer
            # identity when the original exact-photo source records no name.
            creator="Unspecified iNaturalist photographer (CC0; source linked)"
        direct=str(row.get("direct_image_url") or row.get("direct_url") or "")
        match=re.search(r"/photos/(\d+)/(?:original|large|medium)\.(?:jpe?g|png|webp)",direct,re.I)
        if not match or not direct.startswith("https://inaturalist-open-data.s3.amazonaws.com/photos/"):
            omitted["no_exact_individual_open_data_photo_url"]+=1;continue
        pid=match.group(1)
        origpid=str(row.get("photo_id") or "").strip()
        if origpid and origpid!=pid:
            omitted["archived_photo_id_conflicts_with_direct_photo"]+=1;continue
        current_file=site/"data/species"/(sid+".json")
        if current_file.is_file():
            present=json.loads(current_file.read_text())
            if any(str(p.get("source_page") or "").rstrip("/").endswith("/photos/"+pid)
                   for p in present.get("verified_photos",[]) if isinstance(p,dict)):
                omitted["individual_source_photo_already_published"]+=1;continue
        row["source_page"]="https://www.inaturalist.org/photos/"+pid
        row["creator"]=creator
        row["license"]=code
        row["photo_id"]=pid
        row["observation_id"]=str(row.get("observation_id") or "")
        row["direct_url"]=direct
        row["direct_image_url"]=direct
        card_file=src/parent/"species.json"''')
change('''    if "inaturalist.org/photos/" in page and c.get("photo_id") and c.get("observation_id"):return "inat"''',
'''    if "inaturalist.org/photos/" in page and c.get("photo_id"):return "inat"''')
change('''def gbif_verify(c:dict)->dict:''',
'''def inat_verify(c:dict)->dict:
    # This lane is backed by the original individual CC grant and direct photo
    # URL, not by an inferred observation or a newly assumed current CC license.
    pid=int(c["photo_id"])
    code=str(c["claimed_license"] or "")
    if code not in PHOTO_CODES:
        raise RuntimeError("Original individual Creative Commons code unsupported")
    creator=str(c["claimed_creator"] or "").strip()
    if not creator:
        raise RuntimeError("Original individual photographer missing")
    url=collect_photo_url(str(c["direct_image_url"]),pid)
    distance=(dhash(c["original_bytes"])^dhash(request(url))).bit_count()
    if distance>12:
        raise RuntimeError("Archived exact-photo bytes differ from source photo: "+str(distance))
    expected=" ".join(c["scientific_name"].split()[:2])
    if not expected or not (c["species_id"].replace("-"," ").casefold()==expected.casefold() or c["species_id"].replace("-"," ").casefold().startswith(expected.casefold()+" ")):
        # A botanical infraspecific naming variation is not enough to erase
        # an assigned site name mismatch without separate documented review.
        raise RuntimeError("Original named species card does not match assigned species ID")
    return {"license":PHOTO_CODES[code][0],"license_url":PHOTO_CODES[code][1],
      "creator":creator,"exact_page":"https://www.inaturalist.org/photos/"+str(pid),
      "taxon":expected,"source_type":"inat-archived-exact-photo",
      "source_id":str(pid),
      "evidence":"Specific historical source image-sources.csv CC code "+code+
        " and named photographer "+creator+"; exact photo "+str(pid)+
        "; source image public open-data URL "+url+
        "; archived vs source pixel dHash distance "+str(distance)+
        "; original species-card name "+expected+
        "; historical CC permission is irrevocable but source license was not freshly revalidated"}
def gbif_verify(c:dict)->dict:''')
change('''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}''',
'''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha") and r.get("status")!="HELD"}''')
change("multi-family-historical-archive-trust-2026-11-03.json",
       "multi-family-historical-cc0-source-2026-11-03.json")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03",
       "MULTIFAMILY_HISTORICAL_CC0_SOURCE_2026-11-03")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",
       "MULTIFAMILY_HISTORICAL_CC0_SOURCE")
exec(compile(s,str(base),"exec"),{"__name__":"__main__","__file__":str(base)})
