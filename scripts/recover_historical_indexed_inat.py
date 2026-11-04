#!/usr/bin/env python3
"""Publish archived per-photo iNaturalist records with BOTH original observation and
photo IDs, only after exact current image license, author, taxon, hash/pixel checks."""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(old,new,n=1):
    global s
    if s.count(old)!=n:
        raise RuntimeError("Base auditor changed: "+repr(old[:70])+" matches "+str(s.count(old)))
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
change('''        card_file=src/parent/"species.json"''',
'''        obs=str(row.get("observation_id") or "").strip()
        pid=str(row.get("photo_id") or "").strip()
        code=str(row.get("license_code") or row.get("license") or "").lower().strip().replace("_","-").replace(" ","-")
        if code.startswith("cc-by-nc-sa"): code="cc-by-nc-sa"
        elif code.startswith("cc-by-sa"): code="cc-by-sa"
        elif code.startswith("cc-by-nc"): code="cc-by-nc"
        elif code.startswith("cc-by"): code="cc-by"
        elif code.startswith("cc0"): code="cc0"
        creator=str(row.get("attribution") or row.get("creator") or "").strip()
        if not (obs.isdigit() and pid.isdigit() and code in PHOTO_CODES and creator):
            omitted["missing_ids_or_valid_cc_author"]+=1;continue
        current_file=site/"data/species"/(sid+".json")
        if current_file.is_file():
            present=json.loads(current_file.read_text())
            if any(str(p.get("source_page") or "").rstrip("/").endswith("/photos/"+pid)
                   for p in present.get("verified_photos",[]) if isinstance(p,dict)):
                omitted["photo_id_already_public_in_species_card"]+=1;continue
        row=dict(row)
        row["source_page"]="https://www.inaturalist.org/photos/"+pid
        row["creator"]=creator
        row["license"]=code
        row["photo_id"]=pid
        row["observation_id"]=obs
        card_file=src/parent/"species.json"''')
change('''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}''',
'''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}''')
change('''    validate_claim(c.get("claimed_license"),code)''',
'''    validate_claim(c.get("claimed_license"),code)
    if c.get("claimed_license")=="cc0" and code!="cc0":
        raise RuntimeError("Archived CC0 claim not confirmed on current exact photo")''')
change('''    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("Taxon mismatch: "+taxon+" vs "+expected)''',
'''    if len(expected.split())!=2 or not (taxon.casefold()==expected.casefold() or taxon.casefold().startswith(expected.casefold()+" ")):
        raise RuntimeError("Taxon mismatch: "+taxon+" vs "+expected)''')
change('''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}''',
'''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha") and r.get("status")!="HELD"}''')
change("multi-family-historical-archive-trust-2026-11-03.json",
       "multi-family-historical-indexed-inat-2026-11-03.json")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03",
       "MULTIFAMILY_HISTORICAL_INDEXED_INAT_2026-11-03")
change("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",
       "MULTIFAMILY_HISTORICAL_INDEXED_INAT")
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
