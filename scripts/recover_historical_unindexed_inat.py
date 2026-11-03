#!/usr/bin/env python3
"""Recover photos with archived original iNaturalist observation+photo IDs
that were omitted from the original source-selection lane. Uses only exact
live iNaturalist image-specific CC license, photographer, taxon and pixel match.
Never infer permission from an observation license alone.
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(old,new,n=1):
    global s
    if s.count(old)!=n:raise RuntimeError("Original photo auditor changed: "+old[:75])
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
            omitted["prior_source_review_not_overridden"]+=1
            continue''')
change('        card_file=src/parent/"species.json"',
'''        import re
        orig_page=str(row.get("source_page") or "")
        obs_id=str(row.get("observation_id") or "").strip()
        photo_id=str(row.get("photo_id") or "").strip()
        if not obs_id:
            m=re.search(r"inaturalist\\.org/observations/(\\d+)",orig_page)
            obs_id=m.group(1) if m else ""
        if not photo_id:
            direct=str(row.get("direct_url") or row.get("direct_image_url") or "")
            m=re.search(r"(?:inaturalist-open-data\\.s3\\.amazonaws\\.com|static\\.inaturalist\\.org)/photos/(\\d+)/",direct)
            photo_id=m.group(1) if m else ""
        if not (obs_id.isdigit() and photo_id.isdigit() and
                ("inaturalist.org/observations/" in orig_page or
                 "inaturalist.org/photos/" in orig_page)):
            omitted["still_lacks_observation_and_photo_specific_ids"]+=1;continue
        if not (row.get("creator") and row.get("license")):
            omitted["archived_photo_creator_or_license_unknown"]+=1;continue
        card_file=src/parent/"species.json"''')
change('''           "source_page":row.get("source_page") or "","claimed_creator":row.get("creator") or "",''',
'''           "source_page":"https://www.inaturalist.org/photos/"+photo_id,
           "claimed_creator":row.get("creator") or "",''')
change('''           "claimed_license":row.get("license") or "", "photo_id":row.get("photo_id") or "",
           "observation_id":row.get("observation_id") or "", "direct_url":row.get("direct_url") or "",''',
'''           "claimed_license":row.get("license") or "", "photo_id":photo_id,
           "observation_id":obs_id, "direct_url":row.get("direct_url") or "",''')
change('multi-family-historical-archive-trust-2026-11-03.json',
       'multi-family-historical-unindexed-inat-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_UNINDEXED_INAT_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_UNINDEXED_INAT",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
