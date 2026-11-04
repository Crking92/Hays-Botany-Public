#!/usr/bin/env python3
"""Publication-first family batch recovery from the CURRENT historical reconciliation.

Only photographs with a named source-specific CC grant are eligible. Original
archive bytes, hashes, source records, photo IDs and existing gallery credits
are preserved. No guesses about image rights; no new downloads.
Operates within ONE family checkout, with a separate immutable staging worktree.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageOps

CC = {
 "cc0":("CC0 1.0","https://creativecommons.org/publicdomain/zero/1.0/"),
 "by":("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/"),
 "by-sa":("CC BY-SA 4.0","https://creativecommons.org/licenses/by-sa/4.0/"),
 "by-nc":("CC BY-NC 4.0","https://creativecommons.org/licenses/by-nc/4.0/"),
 "by-nc-sa":("CC BY-NC-SA 4.0","https://creativecommons.org/licenses/by-nc-sa/4.0/"),
}
LICENSE = {url:(label,url) for label,url in CC.values()}
EXTS = {".jpg",".jpeg",".png",".webp"}
def gitsha(raw):
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def read_json(path):
 return json.loads(path.read_text(encoding="utf-8"))
def write_json(path,data):
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def dhash(raw):
 with Image.open(io.BytesIO(raw)) as im:
  if im.width*im.height>80000000:raise ValueError("image exceeds pixel cap")
  pixels=list(ImageOps.exif_transpose(im).convert("L").resize((9,8),Image.Resampling.LANCZOS).getdata())
 return sum(1<<i for i in range(64) if pixels[(i//8)*9+(i%8)]>pixels[(i//8)*9+(i%8)+1])
def csv_records(folder):
 path=folder/"image-sources.csv"
 if not path.is_file():return {}
 with path.open(encoding="utf-8-sig",newline="") as f:
  rows=list(csv.DictReader(f))
 result=defaultdict(list)
 for row in rows:
  name=Path(str(row.get("file_name") or row.get("file") or "")).name
  if name:result[name].append(row)
 return result
def grant(row,noncommercial):
 """Require versioned source-record license URL; never infer a CC version."""
 license=str(row.get("license") or row.get("license_code") or "").strip()
 url=str(row.get("license_url") or "").strip().replace("http://","https://")
 url=url.rstrip("/")+"/" if url else ""
 # Photographic source CSVs frequently store cc-by as license_code. But
 # without the particular versioned license URL this is NOT sufficient.
 if not url and license.lower() in ("cc0","cc0 1.0","cc-zero"):
  url=CC["cc0"][1]
 if not url:
  # Exact VERSIONED per-image license declaration is itself a valid grant.
  # Never infer a version from bare CC BY / CC BY-NC / guide shorthand.
  normalized=" ".join(license.upper().replace("-"," ").replace("_"," ").split())
  for label,canonical in CC.values():
   if normalized==" ".join(label.upper().replace("-"," ").split()):
    url=canonical
    break
 if not url or url not in LICENSE:raise ValueError("NO_EXACT_CC_LICENSE_URL")
 code,canon=LICENSE[url]
 if "NC" in code and not noncommercial:raise ValueError("NC_ON_UNVERIFIED_COMMERCIAL_SITE")
 low=license.lower().replace("_","-").replace(" ","")
 if any(w in low for w in ("allrights","rightsreserved","unverified","notcleared","private","studyonly")):
  raise ValueError("SOURCE_RESTRICTS_REUSE")
 if "cc0" in low and not code.startswith("CC0"):raise ValueError("LICENSE_CONFLICT")
 if "by-sa" in low and "SA" not in code:raise ValueError("LICENSE_CONFLICT")
 if "by-nc" in low and "NC" not in code:raise ValueError("LICENSE_CONFLICT")
 if "ccby" in low or low.startswith("cc-"):
  if code.startswith("CC0") and "cc0" not in low:raise ValueError("LICENSE_CONFLICT")
 creator=str(row.get("creator") or row.get("attribution") or "").strip()
 if not creator or any(t in creator.lower() for t in ("unknown","unverified","not stated","unidentified")):
  raise ValueError("NO_VERIFIED_CREATOR")
 if creator.lower().startswith("(c) ") and "some rights reserved" in creator.lower():
  # Preserve source credit rather than stripping attribution.
  pass
 page=str(row.get("source_page") or row.get("observation_url") or "").strip()
 direct=str(row.get("direct_image_url") or row.get("direct_url") or row.get("media_source_url") or "").strip()
 photo_id=str(row.get("photo_id") or "").strip()
 if not page.startswith("https://") and not page.startswith("http://"):
  raise ValueError("NO_SOURCE_PAGE")
 page=page.replace("http://","https://")
 if not (photo_id.isdecimal() or
         page.startswith(("https://commons.wikimedia.org/wiki/File:","https://phytokeys.pensoft.net/article/31738/element/")) or
         (page.startswith("https://www.gbif.org/occurrence/") and "/photos/" in direct)):
  raise ValueError("NO_INDIVIDUAL_PHOTO_PROVENANCE")
 if photo_id and photo_id.isdecimal() and direct and ("/photos/"+photo_id+"/") not in direct:
  raise ValueError("PHOTO_ID_DIRECT_URL_DISAGREE")
 return code,canon,creator,page,photo_id
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--archive",required=True)
 ap.add_argument("--site",default="site")
 ap.add_argument("--repo",required=True)
 ap.add_argument("--reconciliation",required=True)
 ap.add_argument("--limit",type=int,default=90)
 args=ap.parse_args()
 site=Path(args.site); archive=Path(args.archive)
 report=read_json(Path(args.reconciliation))
 fam=next(x for x in report["family_audits"] if x["repository"]==args.repo)
 idxpath=site/"data/collection-index.json";gpath=site/"data/gallery-index.json"
 idx=read_json(idxpath);g=read_json(gpath)
 meta=read_json(site/"data/collection-meta.json")
 noncommercial=meta["photo_license_policy"]["noncommercial_educational_use"] is True
 rows={x["id"]:x for x in idx["entries"]}
 if sum(x["photo_count"] for x in idx["entries"])!=g["photo_count"]:
  raise RuntimeError("Preexisting global photo count inconsistent; no publication")
 for slug,record in rows.items():
  if g["entries"][slug]["count"]!=record["photo_count"]:
   raise RuntimeError("Preexisting species count inconsistent: "+slug)
 cards={};sources={};hashes={};hash_images={};added=Counter();status=Counter();notes=[]
 def classify(r,reason):
  status[reason]+=1;notes.append({"record":r["source_path"],"status":reason})
  if reason!="INSTALLED_PENDING_PUBLIC_VERIFICATION":
   print("HAYS_RECORD_HOLD",r["source_path"],reason,flush=True)
 for r in fam["unmatched_photos"]:
  if r.get("owner_closed_excluded"):
   classify(r,"PERMANENT_EXCLUSION");continue
  if sum(added.values())>=args.limit:
   classify(r,"DEFERRED_CAPACITY");continue
  try:
   pieces=Path(r["source_path"]).parts
   if "images" not in pieces:raise ValueError("COMPARISON_OR_GENUS_MEDIA")
   pos=pieces.index("images")
   if pos<4 or pos!=5:raise ValueError("NON_STANDARD_SPECIES_IMAGE_PATH")
   slug=pieces[pos-1]
   if slug not in rows:raise ValueError("SPECIES_NOT_IN_PUBLIC_GALLERY")
   name=pieces[-1]
   if Path(name).suffix.lower() not in EXTS:raise ValueError("NOT_A_RASTER_PHOTO")
   folder=archive.joinpath(*pieces[:pos])
   if slug not in cards:
    target=site/"data/species"/(slug+".json")
    cards[slug]=(target,read_json(target))
    sourcecard=folder/"species.json"
    sources[slug]=read_json(sourcecard) if sourcecard.is_file() else {}
    hashes[slug]=csv_records(folder)
    hash_images[slug]=[]
    for p in cards[slug][1].get("verified_photos",[]):
     local=site/str(p.get("src",""))
     if local.is_file():
      try:hash_images[slug].append(dhash(local.read_bytes()))
      except Exception:pass
   path,card=cards[slug]
   if card.get("id")!=slug or len(card["verified_photos"])!=rows[slug]["photo_count"]+added[slug]:
    raise ValueError("CARD_INDEX_MISMATCH")
   candidates=hashes[slug].get(name,[])
   if len(candidates)!=1:raise ValueError("NO_SINGLE_EXACT_SOURCE_RECORD")
   row=candidates[0]
   photo_entries=[x for x in sources[slug].get("images",[]) if Path(str(x.get("file") or "")).name==name]
   if len(photo_entries)!=1:raise ValueError("NO_SINGLE_ARCHIVED_SPECIES_IMAGE")
   source=photo_entries[0]
   if str(source.get("public_reuse") or "").strip().lower() in ("no","false","private_study_only"):
    raise ValueError("SOURCE_SPECIFIC_REUSE_HOLD")
   code,lurl,creator,page,pid=grant(row,noncommercial)
   old_license=str(source.get("license") or "").lower()
   if "all rights reserved" in old_license or "private study" in old_license:
    raise ValueError("ARCHIVED_RIGHTS_HOLD")
   if str(source.get("license_url") or ""):
    existing_url=str(source["license_url"]).replace("http://","https://").rstrip("/")+"/"
    if existing_url!=lurl:raise ValueError("SOURCE_CARD_LICENSE_CONFLICT")
   original=archive/r["archive_path"]
   if not original.is_file():raise ValueError("ORIGINAL_MISSING_FROM_STAGING")
   raw=original.read_bytes()
   if gitsha(raw)!=r["source_blob_sha"]:raise ValueError("ARCHIVE_HASH_MISMATCH")
   with Image.open(io.BytesIO(raw)) as im:im.verify()
   photos=card["verified_photos"]
   if any(p.get("source_blob_sha")==r["source_blob_sha"] for p in photos):
    raise ValueError("ALREADY_EXACT")
   if pid and any(pid in str(p.get("source_page","")) for p in photos):
    raise ValueError("ALREADY_SAME_SOURCE_PHOTO_ID")
   fp=dhash(raw)
   if any((fp^other).bit_count()<=2 for other in hash_images[slug]):
    raise ValueError("ALREADY_VISUAL_DUPLICATE")
   file_path="media/"+slug+"/historical-bulk-"+r["source_blob_sha"][:16]+original.suffix.lower()
   dest=site/file_path
   if dest.exists():raise ValueError("DESTINATION_COLLISION")
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
   photo={
    "src":file_path,"creator":creator,"source_page":page,
    "source_page_is_exact":page.startswith("https://commons.wikimedia.org/wiki/File:") or page.startswith("https://www.inaturalist.org/photos/"),
    "license":code,"license_url":lurl,"source_blob_sha":r["source_blob_sha"],
    "role":str(row.get("role") or row.get("diagnostic_role") or "General plant identification photo"),
    "modified":str(row.get("modifications") or source.get("modifications") or "Original archived image; unchanged in this recovery"),
    "noncommercial_only":"NC" in code,"private_rights_review_only":False,
    "photo_approval_mode":"OWNER_STANDING_PHOTO_FIRST_POLICY",
    "photo_approved_by":"Prior photo-specific archive license and attribution record, original source photo reference, and SHA verified; source-only review reused",
    "source_review_evidence":"Exact archived Git blob "+r["source_blob_sha"]+"; source: "+page+"; source media "+str(row.get("direct_image_url") or row.get("direct_url") or row.get("media_source_url") or ""),
    "taxon_review_evidence":"Previously curated exact-species original source record: "+slug+"; new specialist morphology/arrows not claimed",
   }
   photos.append(photo);hash_images[slug].append(fp);added[slug]+=1
   classify(r,"INSTALLED_PENDING_PUBLIC_VERIFICATION")
   print("BULK_INSTALLED",slug,name,code,flush=True)
  except Exception as e:
   classify(r,str(e)[:100])
 for slug,count in added.items():
  path,card=cards[slug];write_json(path,card)
  rows[slug]["photo_count"]+=count
  if not rows[slug].get("photo_publication_status"):
   rows[slug]["photo_publication_status"]="VERIFIED_EXISTING_CC_GALLERY"
  g["entries"][slug]["count"]+=count
  if not g["entries"][slug].get("first_src"):
   g["entries"][slug]["first_src"]=card["verified_photos"][0]["src"]
 if added:
  g["photo_count"]+=sum(added.values())
  g["photo_species"]=sum(r["photo_count"]>0 for r in idx["entries"])
  write_json(idxpath,idx);write_json(gpath,g)
 assert sum(r["photo_count"] for r in idx["entries"])==g["photo_count"]
 assert all(g["entries"][k]["count"]==v["photo_count"] for k,v in rows.items())
 output={"repository":args.repo,"processed":len(fam["unmatched_photos"]),
  "installed_pending_website":sum(added.values()),"species_improved":len(added),
  "gallery_photos_after":g["photo_count"],"statuses":dict(status),"species":dict(added),
  "record_details":notes}
 Path("/tmp/hays-bulk-summary.json").write_text(json.dumps(output,indent=2))
 print("HAYS_90_PHOTO_BATCH_REPORT",json.dumps({k:v for k,v in output.items() if k!="record_details"},sort_keys=True),flush=True)
if __name__=="__main__":main()
