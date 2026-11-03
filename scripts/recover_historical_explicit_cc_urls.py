#!/usr/bin/env python3
"""Recover previously held Commons originals whose source CSV recorded an exact
Creative Commons license URL but only a shorthand textual license label.
The exact original CC URL is existing per-image evidence, not an inferred grant.
Reject class/version mismatches, generic source pages or missing photographer.
"""
from pathlib import Path
source=Path(__file__).with_name("recover_historical_archive_trust.py")
s=source.read_text()
def sub(old,new,n=1):
    global s
    if s.count(old)!=n:raise RuntimeError("Historic per-image rights validator changed: "+old[:90])
    s=s.replace(old,new,n)
a='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
b='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       str(r.get("reason","")).startswith("Archived per-photo rights unverified or unsupported: CC BY")}'''
sub(a,b)
old='''        row=csv_cache[parent].get(fn)
        if not row:
            omitted["no_matching_per_image_csv_row"]+=1;continue
        card_file=src/parent/"species.json"'''
new='''        row=csv_cache[parent].get(fn)
        if not row:
            omitted["no_matching_per_image_csv_row"]+=1;continue
        row=dict(row)
        claim=str(row.get("license") or "").upper().strip()
        url=str(row.get("license_url") or "").strip().replace("http://","https://")
        match=re.fullmatch(r"https://creativecommons\\.org/licenses/(by|by-sa|by-nc|by-nc-sa)/(2\\.0|3\\.0|4\\.0)/?",url)
        if (claim not in ("CC BY","CC BY-SA","CC BY-NC","CC BY-NC-SA") or
            not match or claim!="CC "+match.group(1).upper()):
            omitted["license_shorthand_not_proven_by_original_exact_versioned_url"]+=1;continue
        if not str(row.get("source_page") or "").startswith("https://commons.wikimedia.org/wiki/File:"):
            omitted["not_an_exact_commons_photo_file_page"]+=1;continue
        row["license"]="CC "+match.group(1).upper()+" "+match.group(2)
        card_file=src/parent/"species.json"'''
sub(old,new)
sub('multi-family-historical-archive-trust-2026-11-03.json',
    'multi-family-historical-cc-url-resolved-2026-11-03.json')
sub('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
    '"batch_key":"MULTIFAMILY_HISTORICAL_CC_URL_RESOLVED_2026-11-03"')
sub('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
    'print("MULTIFAMILY_HISTORICAL_CC_URL_RESOLVED",json.dumps({')
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
