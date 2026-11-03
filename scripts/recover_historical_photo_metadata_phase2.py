#!/usr/bin/env python3
"""Hays Botany historical Phase 2: rescue old image-source links from species cards.

Recovers *metadata*, not rights by assumption. Searches old species.json image
metadata where per-image CSV rows or photo/observation identifiers are missing,
then independently checks the current exact photo license, creator, observation
taxon, source image pixels, pinned original Git hash and existing family gallery.
Anything uncertain stays uninstalled and has a saved reason. Shares the same
validator and uploader used by earlier source-linked archive batches.

Only the assigned family repository receives approved media; no new downloads
to its source archive, no edits to original files, and no public uncertain bytes.
"""
import argparse,collections,csv,datetime,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
import recover_historical_multi_family_photos as common

EXT={".jpg",".jpeg",".png",".webp"}
KEYS=("source_page","photo_id","observation_id","creator","license","role",
      "direct_url","direct_image_url","modifications")
def safe_rows(path):
    if not path.is_file():return []
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        return list(csv.DictReader(f))
def sci_name(card):
    return str(card.get("scientific_name") or "").strip()
def norm(x):
    return re.sub(r"\s+"," ",str(x or "").strip())
def source_candidates(img):
    return [img.get(k) for k in ("source_page","source_url","photo_source","original_source_page")
            if img.get(k)]
def matching_original(card, filename):
    ims=[x for x in card.get("images",[]) if isinstance(x,dict)
         and Path(str(x.get("file") or x.get("filename") or "")).name==filename]
    return ims[0] if len(ims)==1 else None
def enrich_row(row,img,filename):
    # If a source CSV contradicts a linked original species image, quarantine
    # rather than pick whichever version would be easier to license.
    if row is None:row={}
    if img is None:img={}
    r=dict(row)
    r.setdefault("file_name",filename)
    for k in KEYS:
        old=norm(r.get(k))
        new=norm(img.get(k))
        if old and new and old!=new and k in ("photo_id","observation_id"):
            raise RuntimeError("Original CSV and species.json disagree on "+k)
        if not old and new:r[k]=new
    if not r.get("source_page"):
        pages=source_candidates(img)
        if pages:r["source_page"]=pages[0]
    for key in ("direct_url","direct_image_url"):
        if not r.get(key):
            r[key]=img.get("media_source_url") or img.get("downloaded_from") or img.get("direct_url") or img.get("direct_image_url") or ""
    if not r.get("photo_id"):
        # A specific photo URL is evidence of a photo ID, not an observation ID.
        photo_url=r.get("source_page") or r.get("direct_url") or r.get("direct_image_url") or ""
        m=re.search(r"(?:inaturalist\.org/photos/|/photos/)(\d+)",photo_url)
        if m:r["photo_id"]=m.group(1)
    if not r.get("observation_id"):
        url=img.get("observation_url") or img.get("observation_page") or ""
        m=re.search(r"inaturalist\.org/observations/(\d+)",str(url))
        if m:r["observation_id"]=m.group(1)
    if not r.get("source_page") and r.get("photo_id") and r.get("observation_id"):
        r["source_page"]="https://www.inaturalist.org/photos/"+str(r["photo_id"])
    return r
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",required=True,type=Path)
    ap.add_argument("--site-root",required=True,type=Path)
    ap.add_argument("--repository",required=True)
    ap.add_argument("--publisher",choices=("family","lamiales"),default="family")
    ap.add_argument("--limit",type=int,default=50)
    ap.add_argument("--audit-only",action="store_true")
    args=ap.parse_args()
    assert 1<=args.limit<=100
    root=args.source_root.resolve();site=args.site_root.resolve()
    policy=json.loads((site/"data/collection-meta.json").read_text())
    assert policy["repository_full_name"]==args.repository
    assert policy["photo_license_policy"]["noncommercial_educational_use"] is True
    manifest=json.loads((root/"migration/original-source-transfer-manifest.json").read_text())
    assert manifest["summary"]["repository"]==args.repository
    gallery=json.loads((site/"data/collection-index.json").read_text())
    assigned={x["id"]:x for x in gallery["entries"]}
    assert len(assigned)==len(gallery["entries"])
    prior_path=site.parent/"workflow/multi-family-historical-recovery-2026-11-03.json"
    prior=json.loads(prior_path.read_text())
    original_review=[r for b in (prior.get("previous_batches") or [])+[prior]
                     for r in b.get("records",[]) if r.get("git_blob_sha")]
    reviewed={r["git_blob_sha"] for r in original_review}
    published_shas={common.blob_sha(p.read_bytes()) for p in (site/"media").rglob("*")
                    if p.is_file() and p.suffix.lower() in EXT}
    report_path=site.parent/"workflow/multi-family-metadata-recovery-phase2-2026-11-03.json"
    older=json.loads(report_path.read_text()) if report_path.is_file() else {}
    previous=list(older.get("previous_batches") or [])
    if older.get("records") is not None:
        previous.append({k:older.get(k) for k in
            ("run_time","selected","installed","held_checked","records")})
    prior_phase2={r.get("git_blob_sha") for b in previous for r in b.get("records",[])
                  if r.get("git_blob_sha")}
    report={
       "repository":args.repository,"phase":"recover_missing_identifiers_from_original_species_records",
       "run_time":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "source_image_file_records":len([r for r in manifest["files"] if r.get("class")=="PRIVATE_MEDIA_HOLD"]),
       "selected":0,"installed":0,"held_checked":0,"duplicate_or_previously_published":0,
       "previous_batches":previous,"skipped":{},"records":[]}
    skip=collections.Counter()
    pool=[]
    image_csv_cache={};species_cache={}
    for r in manifest["files"]:
        if r.get("class")!="PRIVATE_MEDIA_HOLD":continue
        parts=Path(r["source_path"]).parts
        if len(parts)<7 or parts[0:2]!=("content","taxa") or parts[-2]!="images":
            skip["original_path_shape_or_assignment_mismatch"]+=1;continue
        family,sid,filename=parts[2],parts[-3],parts[-1]
        if sid not in assigned or assigned[sid].get("family")!=family:
            skip["species_not_in_assigned_learner"]+=1;continue
        if Path(filename).suffix.lower() not in EXT:
            skip["unsupported_original_image_type"]+=1;continue
        sh=r["git_blob_sha"]
        if sh in published_shas:
            skip["already_published_exact_archive_bytes"]+=1;continue
        if sh in reviewed:
            skip["previous_phase1_review_record"]+=1;continue
        if sh in prior_phase2:
            skip["previous_phase2_decision"]+=1;continue
        image=root/r["destination"]
        expected_archive=(root/"migration/private-original-photo-holds").resolve()
        if not image.resolve().is_relative_to(expected_archive) or not image.is_file():
            skip["original_bytes_unavailable"]+=1;continue
        species_parent=Path(r["source_path"]).parent.parent
        if species_parent not in species_cache:
            card_path=root/species_parent/"species.json"
            species_cache[species_parent]=json.loads(card_path.read_text()) if card_path.is_file() else {}
        original_card=species_cache[species_parent]
        if original_card.get("id")!=sid:
            skip["species_card_missing_or_mismatch"]+=1;continue
        if species_parent not in image_csv_cache:
            csv_path=root/species_parent/"image-sources.csv"
            image_csv_cache[species_parent]=safe_rows(csv_path)
        candidates=[q for q in image_csv_cache[species_parent] if q.get("file_name")==filename]
        if len(candidates)>1:
            skip["ambiguous_per_image_csv_rows"]+=1;continue
        row=candidates[0] if len(candidates)==1 else None
        linked=matching_original(original_card,filename)
        if row is None and linked is None:
            skip["no_source_csv_or_species_card_image_metadata"]+=1;continue
        try:
            data=enrich_row(row,linked,filename)
        except Exception as exc:
            pool.append({"hold_reason":str(exc),"original":r,"sid":sid,"family":family,"filename":filename,"file":image})
            continue
        c={
          "species_id":sid,"family":family,"scientific_name":sci_name(original_card),
          "filename":filename,"original_path":r["source_path"],
          "archive_path":r["destination"],"original_file":image,
          "git_blob_sha":sh,"bytes":r["bytes"],
          "source_page":norm(data.get("source_page")),
          "claimed_creator":norm(data.get("creator")),
          "claimed_license":norm(data.get("license")),
          "photo_id":norm(data.get("photo_id")),
          "observation_id":norm(data.get("observation_id")),
          "direct_url":norm(data.get("direct_url")),
          "direct_image_url":norm(data.get("direct_image_url")),
          "role":norm(data.get("role") or data.get("view")) or "General plant habit or morphology reference",
          "modifications":norm(data.get("modifications")) or "Preserved historical archive photograph, no new modification.",
          "source_metadata_origin":"image-sources.csv + species.json" if row and linked else ("species.json" if linked else "image-sources.csv")
        }
        lane=common.classify(c)
        # Commons source rate-limits are handled in a separate, slower
        # license-review lane; don't hammer it while processing this batch.
        if lane not in ("inat","gbif"):
            skip["not_enough_identifiers_for_verified_inat_or_gbif_source"]+=1
            continue
        c["lane"]=lane
        pool.append(c)
    pool.sort(key=lambda x:(0 if x.get("lane")=="inat" else 1,x["sid"] if "sid" in x else x.get("species_id",""),x["filename"]))
    selected=pool[:args.limit]
    report["candidate_pool"]=len(pool)
    report["selected"]=len(selected)
    report["remaining_candidates"]=len(pool)-len(selected)
    report["selected_lanes"]=dict(collections.Counter(q.get("lane","unclassified") for q in selected))
    approved_shas=set(published_shas)
    with tempfile.TemporaryDirectory(prefix="hays-phase2-source-metadata-") as tmp:
        stage=Path(tmp)
        for c in selected:
            r={
              "species_id":c.get("species_id",c.get("sid")),"filename":c["filename"],
              "git_blob_sha":c["git_blob_sha"] if "git_blob_sha" in c else c["original"]["git_blob_sha"],
              "original_path":c.get("original_path",c.get("original",{}).get("source_path")),
              "lane":c.get("lane","unclassified")
            }
            try:
                if c.get("hold_reason"):raise RuntimeError(c["hold_reason"])
                image=c["original_file"];payload=image.read_bytes()
                if len(payload)!=c["bytes"] or common.blob_sha(payload)!=c["git_blob_sha"]:
                    raise RuntimeError("Original Git blob changed from migration inventory")
                if not 200<len(payload)<25*1024*1024:
                    raise RuntimeError("Outside original photo publishing size constraints")
                if c["git_blob_sha"] in approved_shas:
                    report["duplicate_or_previously_published"]+=1
                    r["status"]="DUPLICATE_SKIPPED";report["records"].append(r);continue
                c["original_bytes"]=payload
                common.dhash(payload)
                verified={"inat":common.inat_verify,"gbif":common.gbif_verify}[c["lane"]](c)
                sid=c["species_id"]
                already=json.loads((site/"data/species"/(sid+".json")).read_text())
                if any(q.get("source_page")==verified["exact_page"] for q in already["verified_photos"]):
                    report["duplicate_or_previously_published"]+=1
                    r["status"]="EXACT_SOURCE_ALREADY_PUBLISHED";report["records"].append(r);continue
                name="archived-phase2-"+hashlib.sha256(payload).hexdigest()[:16]+Path(c["filename"]).suffix.lower()
                dest=stage/"photo-intake/approved"/sid/name
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
                metadata={
                  "species_id":sid,"photo_file":name,"status":"APPROVED_FOR_PUBLIC_FAMILY_SITE",
                  "rights_approved_for_public":True,"taxon_reviewed":True,
                  "approval_mode":"OWNER_STANDING_PHOTO_FIRST_POLICY",
                  "policy_ref":"PHOTO_FIRST_PUBLIC_GALLERY_POLICY_2026-11-02",
                  "review_operator":"Hays Botany Phase2 species-card evidence recovery and live exact-photo rights verifier",
                  "source_review_evidence":"Missing/incomplete historic CSV metadata recovered from original archived "+c["source_metadata_origin"]+
                     ". "+verified["evidence"]+"; original pinned Git blob "+c["git_blob_sha"]+".",
                  "taxon_review_evidence":"Original species card "+sid+" plus live "+verified["source_type"]+
                     " taxon "+verified["taxon"]+" and exact-photo pixel comparison. No specialist anatomy approval claimed.",
                  "approval_note":"Standing photo-first approval after independently confirming exact image license, original photographer, taxon, source bytes, and image similarity.",
                  "creator":verified["creator"],"source_page":verified["exact_page"],"source_page_is_exact":True,
                  "license":verified["license"],"license_url":verified["license_url"],
                  "noncommercial_site_use_confirmed":"NC" in verified["license"],
                  "role":c["role"],"modifications":c["modifications"],
                  "sha256":hashlib.sha256(payload).hexdigest()
                }
                dest.with_name(name+".json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n")
                approved_shas.add(c["git_blob_sha"])
                r.update(status="SOURCE_VERIFIED_READY",source_page=verified["exact_page"],
                    creator=verified["creator"],license=verified["license"],
                    src="media/"+sid+"/"+name,sha256=hashlib.sha256(payload).hexdigest())
            except Exception as exc:
                r.update(status="HELD",reason=str(exc)[:350])
                report["held_checked"]+=1
            report["records"].append(r)
        ready=sum(x["status"]=="SOURCE_VERIFIED_READY" for x in report["records"])
        if ready and not args.audit_only:
            pub=site.parent/"scripts"/("publish_approved_lamiales_photos.py" if args.publisher=="lamiales" else "publish_approved_family_photos.py")
            cmd=[sys.executable,str(pub),"--source-root",str(stage),"--site-root",str(site)]
            for check in (True,False):
                q=subprocess.run(cmd+(["--check"] if check else []),capture_output=True,text=True)
                if q.returncode:raise RuntimeError("Assigned family publisher blocked Phase2 release: "+q.stdout+q.stderr)
                if not check:report["installed"]=json.loads(q.stdout)["installed"]
            if report["installed"]!=ready:raise RuntimeError("Installed file count did not match verified source decisions")
        report["verified_not_published"]=ready-report["installed"]
        report["skipped"]=dict(skip)
        report["held_by_reason"]=dict(collections.Counter(r.get("reason","") for r in report["records"] if r["status"]=="HELD"))
        report["cumulative_installed"]=report["installed"]+sum(b.get("installed",0) for b in previous)
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("PHASE2_HISTORICAL_METADATA_RECOVERY",json.dumps({
       "repository":args.repository,"source_files":report["source_image_file_records"],
       "candidate_pool":report["candidate_pool"],"reviewed":report["selected"],
       "installed":report["installed"],"held":report["held_checked"],
       "already_published":report["duplicate_or_previously_published"],
       "unreviewed":report["remaining_candidates"],"skipped":report["skipped"],
       "holds_by_reason":report["held_by_reason"]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
