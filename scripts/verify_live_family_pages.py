#!/usr/bin/env python3
"""Read-only 9-family Pages smoke test. Do not activate a broken hub link."""
import json,urllib.request,urllib.error,concurrent.futures,time,sys
from pathlib import Path

EXPECTED={
 "Hays-Botany-Asteraceae":180,
 "Hays-Botany-Fabaceae":91,
 "Hays-Botany-Monocots-Aquatics":113,
 "Hays-Botany-Lamiales":102,
 "Hays-Botany-Asterid-Allies":118,
 "Hays-Botany-Cacti-Buttercups":107,
 "Hays-Botany-Spurges-Mallows":130,
 "Hays-Botany-Trees-Shrubs":133,
 "Hays-Botany-Mixed-Families":105
}
def get(url):
 last=None
 for i in range(3):
  try:
   q=urllib.request.Request(url,headers={"User-Agent":"HaysBotany-ReadOnlyFamilySiteSmoke/1.0","Cache-Control":"no-cache"})
   with urllib.request.urlopen(q,timeout=18) as f:
    raw=f.read(350000)
    if not (200<=f.status<300):raise ValueError("HTTP_"+str(f.status))
    return raw
  except Exception as e:
   last=str(e)
   time.sleep(1+i)
 raise RuntimeError(last)
def test(item):
 name,count=item
 base="https://crking92.github.io/"+name+"/"
 rec={"repository":name,"expected_species":count,"base":base,"tested_site":base+"site/"}
 try:
  landing=get(base)
  if b"site/" not in landing and b"<html" not in landing.lower():
   raise ValueError("Root HTML entrypoint missing")
  html=get(base+"site/")
  if b"collection-title" not in html and b"Visual Learner" not in html:
   raise ValueError("Family learner HTML not found")
  raw=get(base+"site/data/collection-index.json")
  doc=json.loads(raw)
  entries=doc["entries"]
  if len(entries)!=count:raise ValueError("Species count mismatch "+str(len(entries)))
  if len({s["id"] for s in entries})!=count:raise ValueError("Duplicate species IDs")
  sample=get(base+"site/data/species/"+entries[0]["id"]+".json")
  card=json.loads(sample)
  if card["id"]!=entries[0]["id"]:
   raise ValueError("Missing exact species index match")
  photos=0
  if name=="Hays-Botany-Asteraceae":
   summary=json.loads(get(base+"site/data/preview-summary.json"))
   if summary.get("strict_public_cc") is not True or summary.get("verified_photo_copies")!=153:
    raise ValueError("Asteraceae exact strict-CC photo release not live yet")
   photos=summary["verified_photo_copies"]
   doc=json.loads(get(base+"site/data/species/achillea-millefolium.json"))
   verified=doc.get("verified_photos") or []
   if not verified:raise ValueError("Asteraceae photo learner missing verified yarrow gallery")
   shot=verified[0]
   if shot["noncommercial_only"] or shot["private_rights_review_only"] or not shot["source_page"].startswith("https://"):
    raise ValueError("Unexpected public gallery rights condition")
   image=get(base+"site/"+shot["src"])
   if image[:3]!=b"\\xff\\xd8\\xff":
    raise ValueError("Source-credited photo path not serving JPEG pixels")
  else:
   if doc.get("site_release_stage")!="PUBLIC_TEXT_ONLY_PREVIEW_PHOTOS_HELD":
    raise ValueError("Current photo-safe publication stage missing")
   if card.get("verified_photos")!=[]:
    raise ValueError("Text-only collection unexpectedly embeds source photos")
  css=get(base+"site/styles.css")
  js=get(base+"site/app.js")
  if not css or b"data/species/" not in js:
   raise ValueError("CSS or card JavaScript missing")
  rec.update({"status":"PASS","species":count,"photos_embedded":photos,"sample":card["id"],
              "index_url":base+"site/data/collection-index.json",
              "public_site_url":base})
 except Exception as e:rec.update({"status":"FAIL","error":str(e)[:230]})
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 results=list(pool.map(test,EXPECTED.items()))
out={"status":"PASS" if all(x["status"]=="PASS" for x in results) else "PARTIAL",
     "families_tested":len(EXPECTED),
     "families_passed":sum(x["status"]=="PASS" for x in results),
     "species_passed":sum(x.get("species",0) for x in results),
     "photos_embedded":sum(x.get("photos_embedded",0) for x in results),
     "includes_poaceae":False,
     "hub_routes_modified":False,
     "results":results}
Path("qa-report").mkdir(exist_ok=True)
Path("qa-report/live-family-pages.json").write_text(json.dumps(out,indent=2)+"\n")
print("HAYS_LIVE_FAMILY_PAGES_SMOKE",json.dumps(out,sort_keys=True),flush=True)
if out["status"]!="PASS":sys.exit(1)
