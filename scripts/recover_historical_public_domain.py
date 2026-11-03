#!/usr/bin/env python3
"""Recover archived exact-photo Commons public-domain releases and official US federal works.
Only photo-specific original rights records; not generic species-site permission.
Never treat public domain as CC0 or reinterpret attribution-only licenses.
"""
from pathlib import Path

source=Path(__file__).with_name("recover_historical_archive_trust.py")
s=source.read_text()
PD={
    "PUBLIC DOMAIN (US GOVERNMENT)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (U.S. FEDERAL GOVERNMENT)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN US FEDERAL GOVERNMENT":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (NATIONAL PARK SERVICE / U.S. FEDERAL WORK)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (U.S. NATIONAL PARK SERVICE)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (USDA ARS)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (USDA)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (USGS)":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
    "PUBLIC DOMAIN (AUTHOR RELEASED)":"PUBLIC DOMAIN (AUTHOR RELEASED)",
    "PUBLIC DOMAIN (CREATOR DEDICATION)":"PUBLIC DOMAIN (AUTHOR RELEASED)",
    "PUBLIC DOMAIN (PD-SELF)":"PUBLIC DOMAIN (AUTHOR RELEASED)",
}
RIGHTS={
    "PUBLIC DOMAIN (U.S. FEDERAL WORK)":"https://www.copyright.gov/title17/92chap1.html#105",
    "PUBLIC DOMAIN (AUTHOR RELEASED)":"https://creativecommons.org/publicdomain/mark/1.0/",
}
def sub(old,new):
    global s
    if s.count(old)!=1: raise ValueError("Historical validator changed: "+old[:50])
    s=s.replace(old,new)
sub('def commons_verify(c:dict)->dict:',
    'ARCHIVE_REUSE_LICENSES.update('+repr(RIGHTS)+')\nPD='+repr(PD)+'\ndef commons_verify(c:dict)->dict:')
sub('    archived_license=str(c.get("claimed_license") or "").strip().upper()',
'''    archived_license=str(c.get("claimed_license") or "").strip().upper()
    archived_license=PD.get(archived_license,archived_license)
    if archived_license=="PUBLIC DOMAIN (U.S. FEDERAL WORK)":
        agency=(str(c.get("claimed_creator") or "")+" "+str(c.get("source_context") or "")).upper()
        names=("USDA","NRCS","U.S. FOREST SERVICE","US FOREST SERVICE","USFS",
               "NATIONAL PARK SERVICE","NPS","USGS","US GEOLOGICAL SURVEY",
               "U.S. FISH","USFWS","NATIONAL AGRICULTURAL LIBRARY",
               "US FEDERAL GOVERNMENT","U.S. FEDERAL GOVERNMENT")
        if not any(n in agency for n in names):
            raise RuntimeError("No documented federal creator or agency for photo")
    if archived_license=="PUBLIC DOMAIN (AUTHOR RELEASED)":
        author=str(c.get("claimed_creator") or "").strip().lower()
        if author in ("unknown","anonymous","none","wikimedia commons","us government"):
            raise RuntimeError("Public-domain creator release author not individually identified")
''')
sub('        card_file=src/parent/"species.json"',
    '        if str(row.get("license") or "").strip().upper() not in PD:\n            omitted["not_an_individual_public_domain_claim"]+=1;continue\n        card_file=src/parent/"species.json"')
sub('           "role":row.get("role") or "General botanical reference",',
    '           "source_context":row.get("source_context") or "",\n           "role":row.get("role") or "General botanical reference",')
sub('multi-family-historical-archive-trust-2026-11-03.json','multi-family-historical-public-domain-2026-11-03.json')
sub('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
    '"batch_key":"MULTIFAMILY_HISTORICAL_PUBLIC_DOMAIN_2026-11-03"')
sub('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
    'print("MULTIFAMILY_HISTORICAL_PUBLIC_DOMAIN",json.dumps({')
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
