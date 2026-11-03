#!/usr/bin/env python3
"""Recover ORIGINAL archived Commons photographs whose exact file-page, photographer
and specific versioned CC reuse license are preserved in their original species
card rather than an indexed CSV row. Strict original bytes and source filename.
No ambiguous image identity, blanket copyright permission or license inference.
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(old,new,n=1):
    global s
    if s.count(old)!=n:
        raise RuntimeError("Pinned photo audit source changed: "+old[:80])
    s=s.replace(old,new,n)
old='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
new='''    previously_reviewed={r.get("git_blob_sha") for r in all_prior
                         if r.get("git_blob_sha")}
    eligible_held=set()'''
change(old,new)
change('''        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue''','''        if sh in previously_reviewed:
            omitted["historical_prior_hold_or_review_preserved"]+=1;continue''')
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
new='''        card_file=src/parent/"species.json"
        if not card_file.is_file():
            omitted["original_species_card_missing"]+=1;continue
        card=json.loads(card_file.read_text())
        if card.get("id")!=sid:
            omitted["original_species_card_mismatch"]+=1;continue
        matches=[i for i in (card.get("images") or [])
                 if isinstance(i,dict) and str(i.get("file") or "").startswith("images/")
                 and Path(str(i.get("file") or "")).name==fn]
        if len(matches)!=1:
            omitted["card_lacks_one_matching_image_entry"]+=1;continue
        img=matches[0]
        original_page=str(img.get("source_page") or "").strip()
        creator=str(img.get("creator") or "").strip()
        license_name=str(img.get("license") or "").strip().upper()
        oldreuse=str(img.get("public_reuse") or "").lower()
        if (not original_page.startswith("https://commons.wikimedia.org/wiki/File:") or
            license_name not in ARCHIVE_REUSE_LICENSES or not creator):
            omitted["exact_commons_page_or_versioned_license_missing"]+=1;continue
        if oldreuse in ("no","private only","all rights reserved") or
           any(q in oldreuse for q in ("permission required","not for public","no redistribution")):
            omitted["original_explicit_rights_hold"]+=1;continue
        # The exact Commons File title must identify this taxon's genus and
        # species, not a generic decorative photo or a different species.
        file_slug=urllib.parse.unquote(original_page.split("/wiki/File:",1)[1]).lower()
        nameparts=str(card.get("scientific_name") or "").lower().split()
        if len(nameparts)<2 or not all(part in file_slug for part in nameparts[:2]):
            omitted["exact_file_title_does_not_identify_original_taxon"]+=1;continue
        row={
          "source_page":original_page,
          "creator":creator,"license":license_name,
          "photo_id":img.get("photo_id") or "",
          "observation_id":img.get("observation_id") or "",
          "direct_url":img.get("downloaded_from") or img.get("direct_image_url")
              or img.get("media_source_url") or "",
          "direct_image_url":img.get("direct_image_url") or "",
          "public_reuse":oldreuse,
          "role":img.get("role") or "General botanical reference",
          "modifications":img.get("modifications") or "Original historical photo; no new changes"
        }
        candidate={'''
# format condition into one logical expression
new=new.replace('if oldreuse in ("no","private only","all rights reserved") or\n           any(q in oldreuse for q in ("permission required","not for public","no redistribution")):',
                'if (oldreuse in ("no","private only","all rights reserved") or\n            any(q in oldreuse for q in ("permission required","not for public","no redistribution"))):')
change(old,new)
change('multi-family-historical-archive-trust-2026-11-03.json',
       'multi-family-historical-card-commons-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_CARD_COMMONS_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_CARD_COMMONS",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
