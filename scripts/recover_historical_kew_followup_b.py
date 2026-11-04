#!/usr/bin/env python3
"""Bulk retry only Kew-verified historical taxonomic synonyms; photo-specific
rights and image fingerprints must still pass independently."""
from pathlib import Path
f=Path(__file__).with_name('recover_historical_archive_trust.py')
s=f.read_text()
pairs='''valeriana-woodsiana|Valerianella radiata|77185698-1
zanthoxylum-clava-herculis-subsp-fruticosum|Zanthoxylum hirsutum|77175410-1
lantana-x-strigocamara|Lantana strigocamara|60444377-2'''
ALIASES={v[0]:(v[1],"https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:"+v[2])
         for row in pairs.splitlines() if row.strip() for v in [row.split("|")]}
def change(old,new,n=1):
 global s
 if s.count(old)!=n:raise RuntimeError("Auditor version changed: "+old[:50])
 s=s.replace(old,new,n)
change('def inat_verify(c:dict)->dict:',
'ALIASES='+repr(ALIASES)+'\ndef synonym(c,taxon):\n    v=ALIASES.get(c["species_id"])\n    return bool(v and (taxon==v[0] or taxon.startswith(v[0]+" ")))\ndef inat_verify(c:dict)->dict:')
a='if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):'
change(a,'if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ") or synonym(c,taxon)):',2)
a='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
b='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and
       (str(r.get("reason","")).startswith("Taxon mismatch:") or
        str(r.get("reason","")).startswith("GBIF source species differs:"))}'''
change(a,b)
change('        card_file=src/parent/"species.json"',
'        if sid not in ALIASES:\n            omitted["unreviewed_taxonomic_mismatch"]+=1;continue\n        card_file=src/parent/"species.json"')
change('        candidate["lane"]=classify(candidate)',
'        candidate["lane"]=classify(candidate)\n        candidate["synonym_kew_url"]=ALIASES[sid][1]')
change('                checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)',
'                checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)\n                checked["evidence"]+="; exact name synonym confirmed by Kew: "+c["synonym_kew_url"]')
change('". Basic source-backed field recognition only; no diagnostic arrow certification.",',
'". Synonym crosschecked with Kew POWO: "+c["synonym_kew_url"]+". Basic source-backed field recognition only; no diagnostic arrow certification.",')
change('multi-family-historical-archive-trust-2026-11-03.json',
'multi-family-historical-kew-followup-b-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
'"batch_key":"MULTIFAMILY_HISTORICAL_KEW_FOLLOWUP_B_B_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
'print("MULTIFAMILY_HISTORICAL_KEW_FOLLOWUP_B",json.dumps({')
exec(compile(s,str(f),'exec'),{'__name__':'__main__','__file__':str(f)})
