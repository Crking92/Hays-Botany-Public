#!/usr/bin/env python3
"""One exact archived NRCS Commons file; original US federal public-domain work.
This wrapper preserves the shared rights and pixel verifier unchanged and
only extends its per-image rights set after checking the original hold ledger.
"""
from pathlib import Path
source=Path(__file__).with_name("recover_verified_429_commons_cc_photos.py")
s=source.read_text()
sha="c729fc394a6bab029f61c8055e6962a44275ed81"
assert s.count("COMMONS_RIGHTS={")==1
entry={
 "page":"https://commons.wikimedia.org/wiki/File:Rhynchospora_colorata_NRCS-002.jpg",
 "creator":"Robert H. Mohlenbrock",
 "url":"https://upload.wikimedia.org/wikipedia/commons/c/c3/Rhynchospora_colorata_NRCS-002.jpg",
 "license":"PUBLIC DOMAIN (U.S. FEDERAL WORK)",
 "license_url":"https://www.copyright.gov/title17/92chap1.html#105"
}
s=s.replace("COMMONS_RIGHTS={","COMMONS_RIGHTS={\n  "+repr(sha)+": "+repr(entry)+",",1)
marker='    report_path=site.parent/"workflow"/"multi-family-commons-direct-cc-recovery-2026-11-03.json"'
assert s.count(marker)==1
extra='''    if any(r.get("status")=="HELD"
               and r.get("git_blob_sha")=="c729fc394a6bab029f61c8055e6962a44275ed81"
               and "Wikimedia current image license URL unsupported"
                   in str(r.get("reason",""))
               for r in archived_decisions):
        cc0_holds.add("c729fc394a6bab029f61c8055e6962a44275ed81")
'''
s=s.replace(marker,extra+marker,1)
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
