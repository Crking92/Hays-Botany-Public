#!/usr/bin/env python3
"""Recover exact iNaturalist observation/photo IDs found in original species cards,
not indexed in historic image-sources CSV. Require current *individual photo*
CC rights, original creator, original image fingerprint, taxon match, and SHA.
Do not override any historically held license or identity decision.
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(old,new,n=1):
    global s
    if s.count(old)!=n:raise RuntimeError("Original audit source unexpectedly changed: "+old[:85])
    s=s.replace(old,new,n)
old='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
new='''    previously_reviewed={r.get("git_blob_sha") for r in all_prior if r.get("git_blob_sha")}
    eligible_held=set()'''
change(old,new)
change('''        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue''','''        if sh in previously_reviewed:
            omitted["prior_historical_review_preserved"]+=1
            continue''')
old='''        row=csv_cache[parent].get(fn)
        if not row:
            omitted["no_matching_per_image_csv_row"]+=1;continue
        card_file=src/parent/"species.json"
        if not card_file.is_file():
            omitted["original_species_card_missing"]+=1;continue
        card=json.loads(card_file.read_text())
        if card.get("id")!=sid:
            omitted["original_species_card_mismatch"]+=1;continue
        candidate={'''
new='''        csvrow=csv_cache[parent].get(fn)
        if csvrow:
            # Original CSV exact source already covered by other published/held lanes.
            csvpage=str(csvrow.get("source_page") or "")
            if ("inaturalist.org/observations/" in csvpage and
                csvrow.get("photo_id") and csvrow.get("observation_id")):
                omitted["already_indexed_exact_inat_photo"]+=1;continue
        card_file=src/parent/"species.json"
        if not card_file.is_file():
            omitted["original_species_card_missing"]+=1;continue
        card=json.loads(card_file.read_text())
        if card.get("id")!=sid:
            omitted["original_species_card_mismatch"]+=1;continue
        images=[i for i in (card.get("images") or [])
                if isinstance(i,dict) and str(i.get("file") or "").startswith("images/")
                and Path(str(i.get("file"))).name==fn]
        if len(images)!=1:
            omitted["original_card_image_record_missing_or_ambiguous"]+=1;continue
        img=images[0]
        observation=str(img.get("observation_id") or "").strip()
        if not observation:
            url=str(img.get("observation_url") or img.get("source_page") or "")
            m=re.search(r"inaturalist\\.org/observations/(\\d+)",url)
            observation=m.group(1) if m else ""
        photo=str(img.get("photo_id") or "").strip()
        direct=str(img.get("downloaded_from") or img.get("direct_image_url")
                   or img.get("media_source_url") or "")
        if not photo:
            m=re.search(r"/photos/(\\d+)(?:/|$)",str(img.get("source_page") or "")+" "+direct)
            photo=m.group(1) if m else ""
        if not (photo.isdigit() and observation.isdigit()):
            omitted["card_lacks_exact_photo_and_observation_ids"]+=1;continue
        if not (img.get("creator") and img.get("license")):
            omitted["card_photo_creator_or_license_missing"]+=1;continue
        row={
            "source_page":"https://www.inaturalist.org/photos/"+photo,
            "creator":img["creator"],"license":img["license"],
            "photo_id":photo,"observation_id":observation,
            "direct_url":direct,"direct_image_url":direct,
            "public_reuse":img.get("public_reuse") or "",
            "role":img.get("role") or "General botanical recognition photo",
            "modifications":img.get("modifications") or
                "Original archived photograph; no additional modifications"
        }
        candidate={'''
change(old,new)
change('''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}''',
'''    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[])
                      if r.get("git_blob_sha") and r.get("status")!="HELD"}''')
change('if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):',
       'if len(expected.split())!=2 or not (taxon.casefold()==expected.casefold() or taxon.casefold().startswith(expected.casefold()+" ")):',2)
change('multi-family-historical-archive-trust-2026-11-03.json','multi-family-historical-card-inat-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_CARD_INAT_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_CARD_INAT",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
