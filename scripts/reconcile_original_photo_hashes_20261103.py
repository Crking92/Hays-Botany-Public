#!/usr/bin/env python3
"""Read-only one-pass audit of original archived photographs vs current family sites.

Does not publish, redownload individual images, grant photo licenses, or mix the
481 historical source-reconciliation records with the original 214 held set.
Reports source-byte matches and conservative likely resized duplicates, so the
next publication run does not duplicate already represented photographs.
"""
from __future__ import annotations
import collections,csv,hashlib,io,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageOps

FAMILIES=(
 "Trees-Shrubs","Lamiales","Monocots-Aquatics","Mixed-Families",
 "Spurges-Mallows","Asterid-Allies","Cacti-Buttercups"
)
EXTS={".jpg",".jpeg",".png",".webp"}
def cmd(*args):
 return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True).strip()
def git_sha(raw):
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def img_features(path):
 try:
  with Image.open(path) as im:
   img=ImageOps.exif_transpose(im)
   if img.width*img.height>80000000:return None
   ratio=img.width/max(img.height,1)
   x=img.convert("RGB").resize((64,64),Image.Resampling.LANCZOS)
   arr=x.tobytes()
   grey=img.convert("L").resize((9,8),Image.Resampling.LANCZOS)
   a=grey.tobytes()
   dhash=sum(1<<i for i in range(64) if a[(i//8)*9+i%8]>a[(i//8)*9+i%8+1])
   return ratio,arr,dhash
 except Exception:return None
def source_index(folder):
 result={}
 if not folder.exists():return result
 with folder.open(encoding="utf-8-sig",errors="replace",newline="") as fh:
  for row in csv.DictReader(fh):
   fn=Path(str(row.get("file_name") or "")).name
   if fn:result[fn]=row
 return result
def ref_token(page):
 import re
 u=str(page or "").lower()
 m=re.search(r"i?n?aturalist.org/photos/(\d+)",u)
 if m:return "inat-photo:"+m.group(1)
 m=re.search(r"commons.wikimedia.org/wiki/file:(.+)$",u)
 if m:return "commons:"+m.group(1).replace("_"," ").strip()
 m=re.search(r"gbif.org/occurrence/(\d+)",u)
 if m:return "gbif:"+m.group(1)
 return ""
def main():
 totals=collections.Counter()
 with tempfile.TemporaryDirectory(prefix="hays-archive-audit-") as temp:
  root=Path(temp)
  for family in FAMILIES:
   repo="Hays-Botany-"+family
   mainroot=root/(family+"-main")
   sr=root/(family+"-archive")
   url="https://github.com/Crking92/"+repo+".git"
   cmd("git","clone","-q","--depth","1","--branch","main","--single-branch",url,str(mainroot))
   commit=cmd("git","-C",str(mainroot),"rev-parse","HEAD")[:12]
   cmd("git","-C",str(mainroot),"fetch","-q","--depth","1","origin","staging/original-source-transfer")
   cmd("git","-C",str(mainroot),"worktree","add","-q","--detach",str(sr),"FETCH_HEAD")
   transfer=json.loads((sr/"migration/original-source-transfer-manifest.json").read_text())
   manifest=[r for r in transfer["files"] if r.get("class")=="PRIVATE_MEDIA_HOLD"]
   report=json.loads((mainroot/"workflow/multi-family-historical-recovery-2026-11-03.json").read_text())
   historical=[r for b in (report.get("previous_batches") or [])+[report] for r in b.get("records",[])]
   held={r["git_blob_sha"] for r in historical if r.get("status")=="HELD" and r.get("git_blob_sha")}
   tracked={r["git_blob_sha"] for r in historical if r.get("git_blob_sha")}
   bysha=set()
   byspecies=collections.defaultdict(list)
   for m in (mainroot/"site/media").rglob("*"):
    if not m.is_file() or m.suffix.lower() not in EXTS:continue
    bysha.add(git_sha(m.read_bytes()))
    sid=m.parent.name
    byspecies[sid].append(m)
   cards={}
   feature_cache={}
   row_cache={}
   counts=collections.Counter()
   strong=[];possible=[];unmatched=[]
   for r in manifest:
    sha=r["git_blob_sha"]
    if sha in bysha:
     counts["exact_media_file"]+=1
     continue
    counts["no_exact_file"]+=1
    if sha in held:counts["original_hold_no_exact"]+=1
    elif sha not in tracked:counts["untracked_no_exact"]+=1
    else:counts["reviewed_no_exact"]+=1
    original=sr/r["destination"]
    path=Path(r["source_path"])
    if len(path.parts)<7 or not original.is_file():
     counts["missing_original_or_path"]+=1
     continue
    sid=path.parts[-3]
    siteimgs=byspecies.get(sid,[])
    if not siteimgs:
     counts["no_public_image_for_species"]+=1
     unmatched.append((sid,path.name))
     continue
    cards.setdefault(sid,(
     json.loads((mainroot/"site/data/species"/(sid+".json")).read_text())
     if (mainroot/"site/data/species"/(sid+".json")).is_file() else {}
    ))
    card=cards[sid]
    sources={x.get("src"):x for x in card.get("verified_photos",[]) if isinstance(x,dict)}
    folder=str(path.parent.parent)
    if folder not in row_cache:row_cache[folder]=source_index(sr/folder/"image-sources.csv")
    orig_row=row_cache[folder].get(path.name,{})
    token=ref_token(orig_row.get("source_page"))
    feat=img_features(original)
    if not feat:
     counts["unreadable_original"]+=1
     continue
    pairs=[]
    for other in siteimgs:
     if other not in feature_cache:feature_cache[other]=img_features(other)
     pub=feature_cache[other]
     if not pub:continue
     ratioerr=abs(feat[0]-pub[0])/max(feat[0],pub[0],0.01)
     if ratioerr>0.035:continue
     diff=(feat[2]^pub[2]).bit_count()
     if diff>11:continue
     mae=sum(abs(a-b) for a,b in zip(feat[1],pub[1]))/len(feat[1])
     sitephoto=sources.get("media/"+sid+"/"+other.name,{})
     same_token=bool(token and token==ref_token(sitephoto.get("source_page")))
     pairs.append((diff,mae,ratioerr,same_token,sitephoto,other))
    if not pairs:
     counts["no_similar_public_image"]+=1
     unmatched.append((sid,path.name))
     continue
    diff,mae,ratioerr,same_token,photo,img=min(pairs,key=lambda x:(x[1],x[0]))
    if ((diff<=3 and mae<=9 and ratioerr<=0.012) or
       (same_token and diff<=6 and mae<=17 and ratioerr<=0.025)):
     counts["high_confidence_resized_variant"]+=1
     strong.append((sid,path.name,img.name,diff,round(mae,1),same_token))
    elif diff<=9 and mae<=31:
     counts["possible_image_variant_hold_review"]+=1
     possible.append((sid,path.name,img.name,diff,round(mae,1)))
    else:
     counts["no_similar_public_image"]+=1
     unmatched.append((sid,path.name))
   totals.update(counts)
   print("ARCHIVE_FAMILY_RECONCILED",json.dumps({
     "repo":repo,"main_sha":commit,"original_photos":len(manifest),
     "exact_file_in_site":counts["exact_media_file"],
     "non_exact":counts["no_exact_file"],
     "original_214_held_still_non_exact":counts["original_hold_no_exact"],
     "untracked_non_exact_not_equivalent_to_481":counts["untracked_no_exact"],
     "high_confidence_same_image_variant":counts["high_confidence_resized_variant"],
     "possible_image_variant":counts["possible_image_variant_hold_review"],
     "no_public_photo_for_species":counts["no_public_image_for_species"],
     "needs_further_source_or_identity_review":counts["no_similar_public_image"],
     "confirmed_variant_examples":strong[:6],"unmatched_examples":unmatched[:6]
   },ensure_ascii=False),flush=True)
  print("ARCHIVE_BULK_RECONCILIATION_SUMMARY",json.dumps(dict(totals),ensure_ascii=False),flush=True)
if __name__=="__main__":main()
