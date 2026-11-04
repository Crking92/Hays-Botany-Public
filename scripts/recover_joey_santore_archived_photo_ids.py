#!/usr/bin/env python3
"""Exact archived Joey Santore iNaturalist photo-ID recovery, with strict source-level CC and pixel checks."""
from pathlib import Path
source=Path(__file__).with_name('recover_historical_archive_trust.py')
s=source.read_text()
def change(old,new):
    global s
    if s.count(old)!=1:raise RuntimeError('Pinned historic photo auditor changed: '+old[:95])
    s=s.replace(old,new,1)
change('def main()->None:', '''PHOTO_IDS={
 'metastelma-barbigerum':{370620160,370620183,370620201},
 'lithospermum-incisum':{260469355,260469376,260469431},
}
_LOOKUPS={}
def photo_observation_id(sid:str,pid:int)->str:
    if sid not in _LOOKUPS:
        found={}
        taxon={'metastelma-barbigerum':'Metastelma barbigerum',
               'lithospermum-incisum':'Lithospermum incisum'}[sid]
        for pg in range(1,6):
            query=urllib.parse.urlencode({'user_id':'joeysantore','taxon_name':taxon,
                       'per_page':200,'page':pg})
            data=request('https://api.inaturalist.org/v1/observations?'+query,json_response=True)
            rows=data.get('results') or []
            for obs in rows:
                for photo in obs.get('photos') or []:
                    if photo.get('id') in PHOTO_IDS[sid]:
                        photo_id=int(photo['id']); obs_id=int(obs['id'])
                        if photo_id in found and found[photo_id]!=obs_id:
                            raise RuntimeError('Photo ID maps to two observations')
                        found[photo_id]=obs_id
            if len(found)>=len(PHOTO_IDS[sid]) or len(rows)<200: break
        _LOOKUPS[sid]=found
    return str(_LOOKUPS[sid].get(pid) or '')
def main()->None:''')
change('''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}''',
'''    processed_historical={r.get("git_blob_sha") for r in all_prior if r.get("git_blob_sha")}
    eligible_held=set()''')
change('''        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue''',
'''        if sid not in PHOTO_IDS or sh in processed_historical:
            omitted["outside_exact_photo_id_batch_or_prior_decision"]+=1; continue''')
change('''        card_file=src/parent/"species.json"''',
'''        import re
        m=re.fullmatch(r"joey-(\\d+)\\.jpg",fn,re.I)
        if not m or int(m.group(1)) not in PHOTO_IDS[sid]:
            omitted["not_selected_exact_original_photo_id"]+=1;continue
        pid=int(m.group(1))
        if str(row.get('source_page') or '').rstrip('/')!='https://www.inaturalist.org/photos/'+str(pid):
            omitted["original_photo_source_does_not_match_id"]+=1;continue
        if str(row.get('creator') or '').strip()!='Joey Santore' or str(row.get('license') or '').strip()!='CC BY-NC':
            omitted["original_photo_creator_or_license_not_confirmed"]+=1;continue
        try: oid=photo_observation_id(sid,pid)
        except Exception as e:
            omitted['individual_observation_lookup_unavailable']+=1
            print('PHOTO_ID_LOOKUP_ISSUE',sid,pid,str(e)[:150],flush=True)
            continue
        if not oid:
            omitted['exact_photo_observation_not_located']+=1;continue
        row=dict(row);row['observation_id']=oid;row['photo_id']=str(pid)
        card_file=src/parent/"species.json"''')
change('multi-family-historical-archive-trust-2026-11-03.json',
       'multi-family-historical-joey-photo-id-recovery-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_JOEY_PHOTO_ID_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_JOEY_PHOTO_ID",json.dumps({')
exec(compile(s,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
