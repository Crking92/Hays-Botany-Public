#!/usr/bin/env python3
"""Reconcile exact Commons Special:Redirect/file URL query links.
Uses already archived file hashes, per-photo photographer, and the *original*
license (never fills in missing licenses or changes restrictions).
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def change(old,new,expected=1):
    global s
    if s.count(old)!=expected:
        raise RuntimeError("Original source-audit version changed: "+old[:90])
    s=s.replace(old,new,expected)
licenses={
 "CC BY 2.5":"https://creativecommons.org/licenses/by/2.5/",
 "CC BY 3.0 DE":"https://creativecommons.org/licenses/by/3.0/de/",
 "CC BY-SA 2.0 CA":"https://creativecommons.org/licenses/by-sa/2.0/ca/",
 "CC BY-SA 2.0 FR":"https://creativecommons.org/licenses/by-sa/2.0/fr/",
 "CC BY-SA 2.1 ES":"https://creativecommons.org/licenses/by-sa/2.1/es/",
 "CC BY-SA 2.5 AU":"https://creativecommons.org/licenses/by-sa/2.5/au/",
 "CC BY-SA 3.0 RS":"https://creativecommons.org/licenses/by-sa/3.0/rs/",
 "PUBLIC DOMAIN (U.S. FEDERAL WORK)":"https://www.copyright.gov/title17/92chap1.html#105",
 "PUBLIC DOMAIN (AUTHOR RELEASED)":"https://creativecommons.org/publicdomain/mark/1.0/",
}
aliases={
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
 "CC BY-SA 3.0 SERBIA":"CC BY-SA 3.0 RS",
 "CC BY-SA 2.1 SPAIN":"CC BY-SA 2.1 ES",
 "CC BY-SA 2.0 FRANCE":"CC BY-SA 2.0 FR",
 "CC BY-SA 2.0 CANADA":"CC BY-SA 2.0 CA",
 "CC BY-SA 2.5 AUSTRALIA":"CC BY-SA 2.5 AU",
}
change('def commons_verify(c:dict)->dict:',
    'ARCHIVE_REUSE_LICENSES.update('+repr(licenses)+')\nALIASES='+repr(aliases)+'\ndef commons_verify(c:dict)->dict:')
change('    archived_license=str(c.get("claimed_license") or "").strip().upper()',
'''    archived_license=str(c.get("claimed_license") or "").strip().upper()
    archived_license=ALIASES.get(archived_license,archived_license)
    if archived_license=="PUBLIC DOMAIN (U.S. FEDERAL WORK)":
        ctx=(str(c.get("claimed_creator") or "")+" "+str(c.get("source_context") or "")).upper()
        agencies=("USDA","NRCS","US FOREST","U.S. FOREST","USGS","NPS","NATIONAL PARK SERVICE","USFWS","U.S. FISH")
        if not any(t in ctx for t in agencies):
            raise RuntimeError("Archived photograph lacks specific federal agency evidence")
''')
change('        from_direct=re.sub(r"[^a-z0-9]","",urllib.parse.unquote(d.path).lower())',
'''        if d.path=="/w/index.php":
            q=urllib.parse.parse_qs(d.query)
            target=q.get("title",[""])[0]
            if not target.startswith("Special:Redirect/file/"):
                raise RuntimeError("Commons query does not reference an individual file")
            path_photo=target.split("Special:Redirect/file/",1)[1]
        else:
            path_photo=urllib.parse.unquote(d.path)
        from_direct=re.sub(r"[^a-z0-9]","",path_photo.lower())''')
start='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
end='''    for old_name in ("multi-family-historical-archive-trust-2026-11-03.json",
                     "multi-family-historical-ported-cc-2026-11-03.json",
                     "multi-family-historical-public-domain-2026-11-03.json"):
        p=site.parent/"workflow"/old_name
        if p.is_file():
            previous=json.loads(p.read_text())
            for batch in (previous.get("previous_batches") or [])+[previous]:
                all_prior.extend(batch.get("records") or [])
    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and
       "Historic direct photo media URL does not match exact Commons file page" in str(r.get("reason",""))}'''
change(start,end)
change('           "role":row.get("role") or "General botanical reference",',
       '           "source_context":row.get("source_context") or "",\n           "role":row.get("role") or "General botanical reference",')
change('    report_path=site.parent/"workflow"/"multi-family-historical-archive-trust-2026-11-03.json"',
       '    report_path=site.parent/"workflow"/"multi-family-historical-redirect-fix-2026-11-03.json"')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_REDIRECT_FIX_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_REDIRECT_FIX",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
