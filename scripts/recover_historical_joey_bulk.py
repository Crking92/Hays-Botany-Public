#!/usr/bin/env python3
"""Bulk archived Joey Santore iNaturalist photo-ID recovery, with strict source-level CC and pixel checks."""
from pathlib import Path
source=Path(__file__).with_name('recover_historical_archive_trust.py')
s=source.read_text()
def change(old,new):
    global s
    if s.count(old)!=1:raise RuntimeError('Pinned historic photo auditor changed: '+old[:95])
    s=s.replace(old,new,1)
change('def main()->None:', '''PHOTO_IDS={
 "buddleja-racemosa":{373982289,373982378,373982455},
 "carya-illinoinensis":{201569747,201569780,201569819},
 "cnidoscolus-texanus":{97833582,97833631,97833706},
 "coryphantha-echinus":{241108446,241108473},
 "coryphantha-sulcata":{202575423,202575442,202575456},
 "cylindropuntia-imbricata":{375383652,375383692},
 "delphinium-carolinianum":{370255289,370255311,370255326},
 "epipactis-gigantea":{370145480,370145511,370145540},
 "euploca-tenella":{205825167,205825192,714169528},
 "evolvulus-sericeus":{515220574,515220629,515220667},
 "frangula-caroliniana":{332919957,332919973,332919991},
 "galphimia-angustifolia":{332716807,332716829,332716855},
 "ipomopsis-rubra":{515260361,515260398,515260426},
 "linaria-texana":{357336521,357336539,357336563},
 "lindera-benzoin":{377489439,377489474,377489505},
 "linum-rupestre":{48575191,48575206,48575225},
 "marrubium-vulgare":{211367551,211367563},
 "melia-azedarach":{364804436,364804504},
 "melochia-pyramidata":{729727077,729727141,729727206},
 "mirabilis-linearis":{210992272,210992330},
 "morus-microphylla":{202575987,202576006,202576021},
 "nicotiana-obtusifolia":{99685646,99685703,99685732},
 "nolina-lindheimeriana":{375934773,375934832,524128353},
 "oenothera-macrocarpa":{369796316,369796344,369796373},
 "phlox-drummondii":{357407267,357407297,357407311},
 "phoradendron-leucarpum":{357290356,357290384,357290425},
 "pilostyles-thurberi":{201291379,201291412,201291443},
 "rhynchosida-physocalyx":{498675715,498675761},
 "sabal-mexicana":{254471398,254471435},
 "sabatia-campestris":{186051619,186051647},
 "samolus-ebracteatus":{99688428,99688455,99688483},
 "schinus-terebinthifolia":{626401530,626401570},
 "schoenocaulon-texanum":{260230513,260230536,260230550},
 "senega-alba":{260388773,260388784,260388800},
 "talinum-aurantiacum":{162352666,162352679,162352690},
 "viburnum-rufidulum":{730245602,730245660,730245709},
 "zephyranthes-drummondii":{201102983,201103006,201103027},
}
_LOOKUPS={}
def photo_observation_id(sid:str,pid:int)->str:
    if sid not in _LOOKUPS:
        found={}
        taxon=sid.replace("-", " ")
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
        # A resized/renamed public card photo with the same source ID is still a duplicate.
        present=site/"data/species"/(sid+".json")
        if present.is_file():
            live_card=json.loads(present.read_text())
            if any(str(p.get("source_page") or "").rstrip("/").endswith("/photos/"+str(pid))
                   for p in live_card.get("verified_photos",[]) if isinstance(p,dict)):
                omitted["same_individual_photo_already_on_site"]+=1;continue
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
       'multi-family-historical-joey-bulk-2026-11-03.json')
change('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
       '"batch_key":"MULTIFAMILY_HISTORICAL_JOEY_BULK_2026-11-03"')
change('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
       'print("MULTIFAMILY_HISTORICAL_JOEY_BULK",json.dumps({')
exec(compile(s,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
