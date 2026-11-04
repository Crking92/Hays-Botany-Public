#!/usr/bin/env python3
"""Recover original iNaturalist photos using image-level source cards as fallback for missing source CSV rows.
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
change('''        row=csv_cache[parent].get(fn)
        if not row:
            omitted["no_matching_per_image_csv_row"]+=1;continue
        card_file=src/parent/"species.json"''',
'''        row=csv_cache[parent].get(fn)
        if not row:
            cardpath=src/parent/"species.json"
            if not cardpath.is_file():
                omitted["no_source_card_for_missing_csv_row"]+=1;continue
            original_card=json.loads(cardpath.read_text())
            matching=[i for i in original_card.get("images",[]) if isinstance(i,dict)
                and Path(str(i.get("file") or "")).name==fn]
            if len(matching)!=1:
                omitted["no_unique_source_card_image"]+=1;continue
            img=matching[0]
            exact=str(img.get("source_page") or "").rstrip("/")
            match=re.fullmatch(r"https://www\.inaturalist\.org/photos/(\d+)",exact)
            if not match:
                omitted["missing_exact_inat_source_page"]+=1;continue
            pid=match.group(1)
            if str(img.get("photo_id") or img.get("source_photo_id") or pid)!=pid:
                omitted["source_card_photo_identifier_conflict"]+=1;continue
            direct=str(img.get("downloaded_from") or img.get("direct_image_url")
                or img.get("media_source_url") or "")
            if not direct:
                # Exact original source ID must match downloaded bytes before use.
                direct="https://inaturalist-open-data.s3.amazonaws.com/photos/"+pid+"/large.jpg"
            row={"file_name":fn,"license":img.get("license") or "",
                 "creator":img.get("creator") or "",
                 "source_page":exact,"photo_id":pid,
                 "direct_image_url":direct,
                 "role":img.get("role") or "General original plant reference",
                 "modifications":img.get("modifications") or
                     "Original archive photo, preserved without new alterations"}
        card_file=src/parent/"species.json"''')
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
        if not code or not creator or any(term in creator.casefold() for term in vague):
            omitted["no_specific_named_cc_license_and_author"]+=1;continue
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
    initial=str(c["direct_image_url"])
    urls=[initial]
    if initial.startswith("https://inaturalist-open-data.s3.amazonaws.com/photos/"):
        baseurl=initial.rsplit("/",1)[0]
        urls += [baseurl+"/large."+ext for ext in ("jpg","jpeg","png")]
    tries=[]
    for candidate in dict.fromkeys(urls):
        try:
            safe=collect_photo_url(candidate,pid)
            difference=(dhash(c["original_bytes"])^dhash(request(safe))).bit_count()
            tries.append((difference,safe))
            if difference<=12:break
        except Exception:continue
    if not tries or min(x[0] for x in tries)>12:
        raise RuntimeError("Archived exact-photo bytes do not match source photo")
    distance,url=min(tries)
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
       "multi-family-historical-source-card-cc-2026-11-03.json")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03",
       "MULTIFAMILY_HISTORICAL_SOURCE_CARD_CC_2026-11-03")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",
       "MULTIFAMILY_HISTORICAL_SOURCE_CARD_CC")
exec(compile(s,str(base),"exec"),{"__name__":"__main__","__file__":str(base)})
