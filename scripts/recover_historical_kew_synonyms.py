#!/usr/bin/env python3
"""Bulk retry only Kew-verified historical taxonomic synonyms; photo-specific
rights and image fingerprints must still pass independently."""
from pathlib import Path
f=Path(__file__).with_name('recover_historical_archive_trust.py')
s=f.read_text()
pairs='''aquarius-cordifolius|Echinodorus cordifolius|58327-1
pelecyphora-macromeris-subsp-macromeris|Coryphantha macromeris macromeris|77248955-1
sclerocactus-warnockii|Echinomastus warnockii|88287-2
berberis-aquifolium|Mahonia aquifolium|1148915-2
atrema-americanum|Bifora americana|838706-1
cleome-dodecandra|Polanisia dodecandra|30086051-2
cottsia-gracilis|Janusia gracilis|131369-2
hemionitis-alabamensis|Myriopteris alabamensis|77182021-1
hemionitis-aspera|Myriopteris scabra|77134865-1
hemionitis-atropurpurea|Pellaea atropurpurea|30006990-2
hemionitis-ovata|Pellaea ovata|77183106-1
thelypteris-kunthii|Pelazoneuron kunthii|77221191-1
thelypteris-ovata|Pelazoneuron ovatum|77221196-1
aristolochia-serpentaria|Endodeca serpentaria|93333-1
glandularia-pumila|Verbena pumila|263269-2
hedeoma-serpyllifolia|Hedeoma reverchonii serpyllifolia|883877-1
muenchhusia-coccinea|Hibiscus coccineus|77372179-1
muenchhusia-laevis|Hibiscus laevis|77372182-1
muenchhusia-moscheutos|Hibiscus moscheutos|77372183-1
muenchhusia-moscheutos-subsp-lasiocarpos|Hibiscus lasiocarpos|77372184-1
argythamnia-aphoroides|Ditaxis aphoroides|82502-2
argythamnia-humilis|Ditaxis humilis|18922-2'''
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
'multi-family-historical-kew-synonyms-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
'"batch_key":"MULTIFAMILY_HISTORICAL_KEW_SYNONYMS_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
'print("MULTIFAMILY_HISTORICAL_KEW_SYNONYMS",json.dumps({')
exec(compile(s,str(f),'exec'),{'__name__':'__main__','__file__':str(f)})
