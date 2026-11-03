#!/usr/bin/env python3
"""Retry historically held Commons originals with explicitly versioned CC country ports.
Retains exact original license/version and source credits, never converts ported
licenses to generic equivalents. All other archived records remain untouched.
"""
from pathlib import Path

base=Path(__file__).with_name("recover_historical_archive_trust.py")
code=base.read_text()
PORTS={
 "CC BY-SA 3.0 SERBIA":"CC BY-SA 3.0 RS",
 "CC BY-SA 3.0 RS":"CC BY-SA 3.0 RS",
 "CC BY-SA 2.1 SPAIN":"CC BY-SA 2.1 ES",
 "CC BY-SA 2.5 AUSTRALIA":"CC BY-SA 2.5 AU",
 "CC BY-SA 2.0 CANADA":"CC BY-SA 2.0 CA",
 "CC BY-SA 2.0 FRANCE":"CC BY-SA 2.0 FR",
 "CC BY 3.0 DE":"CC BY 3.0 DE",
 "CC BY 2.5":"CC BY 2.5",
}
LICENSES={
 "CC BY-SA 3.0 RS":"https://creativecommons.org/licenses/by-sa/3.0/rs/",
 "CC BY-SA 2.1 ES":"https://creativecommons.org/licenses/by-sa/2.1/es/",
 "CC BY-SA 2.5 AU":"https://creativecommons.org/licenses/by-sa/2.5/au/",
 "CC BY-SA 2.0 CA":"https://creativecommons.org/licenses/by-sa/2.0/ca/",
 "CC BY-SA 2.0 FR":"https://creativecommons.org/licenses/by-sa/2.0/fr/",
 "CC BY 3.0 DE":"https://creativecommons.org/licenses/by/3.0/de/",
 "CC BY 2.5":"https://creativecommons.org/licenses/by/2.5/",
}
def sub_one(old,new):
 global code
 if code.count(old)!=1: raise RuntimeError("Unexpected original photo audit version: "+old[:60])
 code=code.replace(old,new)
sub_one('def commons_verify(c:dict)->dict:',
  'ARCHIVE_REUSE_LICENSES.update('+repr(LICENSES)+')\nPORTS='+repr(PORTS)+'\ndef commons_verify(c:dict)->dict:')
sub_one('    archived_license=str(c.get("claimed_license") or "").strip().upper()',
 '    archived_license=str(c.get("claimed_license") or "").strip().upper()\n    archived_license=PORTS.get(archived_license,archived_license)')
sub_one('        card_file=src/parent/"species.json"',
 '        if str(row.get("license") or "").strip().upper() not in PORTS:\n            omitted["not_an_explicit_older_cc_license"]+=1;continue\n        card_file=src/parent/"species.json"')
sub_one('multi-family-historical-archive-trust-2026-11-03.json',
        'multi-family-historical-ported-cc-2026-11-03.json')
sub_one('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
        '"batch_key":"MULTIFAMILY_HISTORICAL_PORTED_CC_2026-11-03"')
sub_one('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
        'print("MULTIFAMILY_HISTORICAL_PORTED_CC",json.dumps({')
exec(compile(code,str(base), "exec"),{"__name__":"__main__","__file__":str(base)})
