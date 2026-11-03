#!/usr/bin/env python3
"""Source-specific recheck of Pl@ntNet via GBIF image holds, Phase 2.

Only a previously held exact GBIF StillImage from the Pl@ntNet observations
dataset is considered. GBIF's occurrence-wide CC BY is NOT an image licence.
Requires image-specific creator and "(cc-by-sa)", exact source-image URL,
the archived CSV rights claim, original blob hash, identity and live pixel match.
Uses official Pl@ntNet image terms specifying CC BY-SA 2.0 France for API images:
https://my.plantnet.org/documents/copyright_licence_PlantNet_API_english_v5_EUR.pdf
Any different source, licence, author or plant stays held.
"""
from __future__ import annotations
import argparse,collections,csv,datetime,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
import recover_historical_multi_family_photos as common

PLANTNET_DATASET="7a3679ef-5582-4aaa-81f0-8c2545cafc81"
PLANTNET_PUBLISHER="da86174a-a605-43a4-a5e8-53d484152cd3"
LICENSE="CC BY-SA 2.0 FR"
LICENSE_URL="https://creativecommons.org/licenses/by-sa/2.0/fr/"
EVIDENCE="https://my.plantnet.org/documents/copyright_licence_PlantNet_API_english_v5_EUR.pdf"
PLANTNET_HOST="https://bs.plantnet.org/image/o/"
def row_from_csv(path,filename):
    if not path.is_file():raise RuntimeError("Original image source CSV not found")
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as fh:
        matches=[r for r in csv.DictReader(fh) if r.get("file_name")==filename]
    if len(matches)!=1:raise RuntimeError("Image source CSV does not uniquely match archived image")
    return matches[0]
def media_for(c,record):
    occid=re.fullmatch(r"https://www.gbif.org/occurrence/(\d+)",str(record.get("source_page") or ""))
    if not occid:raise RuntimeError("Archive does not identify an individual GBIF occurrence")
    obj=common.request("https://api.gbif.org/v1/occurrence/"+occid.group(1),json_response=True)
    if obj.get("datasetKey")!=PLANTNET_DATASET or obj.get("publishingOrgKey")!=PLANTNET_PUBLISHER:
        raise RuntimeError("Current GBIF dataset is not the individually licensed Pl@ntNet observations source")
    species=obj.get("species") or obj.get("scientificName") or ""
    expected=" ".join(c["scientific_name"].split()[:2])
    if not (species==expected or species.startswith(expected+" ")):
        raise RuntimeError("Source observation scientific name differs from archive: "+species+" / "+expected)
    url=str(record.get("direct_url") or record.get("direct_image_url") or "")
    # Exact hashed image reference must match GBIF media, not a nearby thumbnail
    if not re.fullmatch(r"https://bs\.plantnet\.org/image/o/[a-f0-9]{40}",url):
        raise RuntimeError("Original Pl@ntNet image URL does not have a unique source hash")
    media=[m for m in (obj.get("media") or []) if m.get("identifier")==url]
    if len(media)!=1:raise RuntimeError("The exact original image is not unique in the live GBIF occurrence")
    item=media[0]
    source_author=str(item.get("creator") or item.get("rightsHolder") or "")
    if not common.creator_matches(record.get("creator"),source_author):
        raise RuntimeError("Exact Pl@ntNet photo author differs from archived image-source credit")
    code=str(item.get("license") or "")
    match=re.fullmatch(r"\s*(.*?)\s*\(cc-by-sa\)\s*",code,flags=re.I)
    if not match or not common.creator_matches(source_author,match.group(1)):
        raise RuntimeError("Exact image does not state same author under Pl@ntNet cc-by-sa media license")
    # Do not substitute occurrence-level CC BY 4.0 for image-specific CC BY-SA
    claim=str(record.get("license") or "").upper().replace(" ","-")
    if claim!="CC-BY-SA" and not claim.startswith("CC-BY-SA-"):
        raise RuntimeError("Archived individual image did not claim CC BY-SA")
    url_source=str(item.get("source") or obj.get("references") or "")
    if not url_source.startswith("https://identify.plantnet.org/") or "/observations/" not in url_source:
        raise RuntimeError("Live Pl@ntNet observation source link is absent")
    if item.get("type")!="StillImage":
        raise RuntimeError("GBIF media is not a still photograph")
    original=c["original_bytes"]
    current=common.request(url,json_response=False)
    distance=(common.dhash(original)^common.dhash(current)).bit_count()
    if distance>12:
        raise RuntimeError("Original archived photo differs from current individually licensed source image: "+str(distance))
    return {"creator":common.creator_display(source_author)+" / Pl@ntNet",
            "license":LICENSE,"license_url":LICENSE_URL,"exact_page":"https://www.gbif.org/occurrence/"+str(obj["key"]),
            "image_url":url,"image_source":url_source,"taxon":species,"distance":distance,
            "evidence":"Current GBIF individual StillImage "+url+" of dataset "+PLANTNET_DATASET+
            " has author "+source_author+" and media license field "+code+
            "; official Pl@ntNet API image terms identify CC BY-SA 2.0 France "+
            EVIDENCE+"; original archive Git blob "+c["git_blob_sha"]+
            "; same-image fingerprint distance "+str(distance)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--site-root",type=Path,required=True)
    p.add_argument("--repository",required=True)
    p.add_argument("--publisher",choices=("family","lamiales"),default="family")
    p.add_argument("--limit",type=int,default=40)
    a=p.parse_args()
    assert 1<=a.limit<=50
    root=a.source_root.resolve();site=a.site_root.resolve()
    meta=json.loads((site/"data/collection-meta.json").read_text())
    assert meta["repository_full_name"]==a.repository
    index=json.loads((site/"data/collection-index.json").read_text())
    assigned={x["id"]:x for x in index["entries"]}
    m=json.loads((root/"migration/original-source-transfer-manifest.json").read_text())
    assert m["summary"]["repository"]==a.repository
    previous_report=json.loads((site.parent/"workflow/multi-family-historical-recovery-2026-11-03.json").read_text())
    all_records=[*(x for b in previous_report.get("previous_batches",[]) for x in b.get("records",[])),
                 *previous_report.get("records",[])]
    selected_holds=[x for x in all_records if x.get("status")=="HELD" and "Unsupported GBIF individual media license" in x.get("reason","")]
    source_lookup={v.get("source_path"):v for v in m["files"] if v.get("class")=="PRIVATE_MEDIA_HOLD"}
    prior_file=site.parent/"workflow/multi-family-plantnet-rights-phase2-2026-11-03.json"
    earlier=json.loads(prior_file.read_text()) if prior_file.exists() else {}
    batches=list(earlier.get("previous_batches") or [])
    if earlier.get("records") is not None:
        batches.append({k:earlier.get(k) for k in ("checked_at","selected","published","held","records")})
    decided={z.get("original_path") for b in batches for z in b.get("records",[]) if z.get("original_path")}
    eligible=[x for x in selected_holds if x.get("original_path") not in decided]
    gallery_photos={q.get("source_blob_sha") for f in (site/"data/species").glob("*.json")
                    for q in json.loads(f.read_text()).get("verified_photos",[])}
    report={"repository":a.repository,"phase":"Pl@ntNet exact image-source CC BY-SA 2.0 FR recheck",
            "source_evidence":EVIDENCE,"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "candidate_pool":len(eligible),"selected":0,"published":0,"already_published":0,"held":0,
            "remaining_candidates":0,"previous_batches":batches,"records":[]}
    with tempfile.TemporaryDirectory(prefix="hays-plantnet-source-rights-") as temp:
        stage=Path(temp)
        for old in eligible[:a.limit]:
            original_path=old["original_path"]
            item={"species_id":old["species_id"],"original_path":original_path}
            try:
                src=source_lookup.get(original_path)
                if not src:raise RuntimeError("Exact original source missing from migration manifest")
                parts=Path(original_path).parts
                if len(parts)<7 or parts[-2]!="images":raise RuntimeError("Original archived path malformed")
                sid=parts[-3];family=parts[2]
                if sid!=old["species_id"] or sid not in assigned or assigned[sid]["family"]!=family:
                    raise RuntimeError("Species/family routing changed")
                image=root/src["destination"]
                assert image.is_file() and image.resolve().is_relative_to((root/"migration/private-original-photo-holds").resolve()),"Original archived photo missing"
                payload=image.read_bytes()
                if len(payload)!=src["bytes"] or common.blob_sha(payload)!=src["git_blob_sha"]:
                    raise RuntimeError("Archived original bytes differ from pinned migration manifest")
                if src["git_blob_sha"] in gallery_photos:
                    item["status"]="ALREADY_PUBLISHED";report["already_published"]+=1;report["records"].append(item);continue
                species_card=json.loads((root/Path(original_path).parent.parent/"species.json").read_text())
                assert species_card.get("id")==sid
                csv_path=root/Path(original_path).parent.parent/"image-sources.csv"
                csvrow=row_from_csv(csv_path,Path(original_path).name)
                candidate={"scientific_name":species_card.get("scientific_name"),"git_blob_sha":src["git_blob_sha"],"original_bytes":payload}
                approved=media_for(candidate,csvrow)
                if any(p.get("source_page")==approved["exact_page"] and
                       p.get("creator")==approved["creator"] for p in
                       json.loads((site/"data/species"/(sid+".json")).read_text())["verified_photos"]):
                    item["status"]="ALREADY_PUBLISHED";report["already_published"]+=1;report["records"].append(item);continue
                fname="plantnet-archive-"+hashlib.sha256(payload).hexdigest()[:16]+Path(original_path).suffix.lower()
                dest=stage/"photo-intake/approved"/sid/fname
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
                note=str(csvrow.get("modifications") or "Archived source image reproduced without further changes")
                sidecar={
                    "species_id":sid,"photo_file":fname,"status":"APPROVED_FOR_PUBLIC_FAMILY_SITE",
                    "rights_approved_for_public":True,"taxon_reviewed":True,
                    "approval_mode":"OWNER_STANDING_PHOTO_FIRST_POLICY",
                    "policy_ref":"PHOTO_FIRST_PUBLIC_GALLERY_POLICY_2026-11-02",
                    "review_operator":"Source-specific Hays Botany GBIF/Pl@ntNet live-image and archived-image verification",
                    "source_review_evidence":approved["evidence"],
                    "taxon_review_evidence":"Current Pl@ntNet contributor identification "+approved["taxon"]+
                       " matches the original image's botanical scientific name "+candidate["scientific_name"]+
                       "; same pixel source verified, specialist diagnostic morphology deferred.",
                    "approval_note":"Owner-standing release after exact photograph, provenance, licensing version, photographer, original archived hash, and current-image match verified; Pl@ntNet credit retained.",
                    "creator":approved["creator"],"source_page":approved["exact_page"],"source_page_is_exact":True,
                    "license":LICENSE,"license_url":LICENSE_URL,"noncommercial_site_use_confirmed":False,
                    "role":str(csvrow.get("role") or csvrow.get("view") or "General botanical reference"),
                    "modifications":note,"sha256":hashlib.sha256(payload).hexdigest()
                }
                dest.with_name(fname+".json").write_text(json.dumps(sidecar,ensure_ascii=False,indent=2)+"\n")
                item.update(status="SOURCE_VERIFIED_READY",creator=approved["creator"],license=LICENSE,
                   source_page=approved["exact_page"],src="media/"+sid+"/"+fname,
                   sha256=hashlib.sha256(payload).hexdigest(),evidence=approved["evidence"])
            except Exception as exc:
                item.update(status="HELD",reason=str(exc)[:500]);report["held"]+=1
            report["records"].append(item)
        report["selected"]=len(report["records"])
        report["remaining_candidates"]=len(eligible)-len(report["records"])
        ready=sum(i["status"]=="SOURCE_VERIFIED_READY" for i in report["records"])
        if ready:
            pub=site.parent/"scripts"/("publish_approved_lamiales_photos.py" if a.publisher=="lamiales" else "publish_approved_family_photos.py")
            args=[sys.executable,str(pub),"--source-root",str(stage),"--site-root",str(site)]
            for check in (True,False):
                res=subprocess.run(args+(["--check"] if check else []),capture_output=True,text=True)
                if res.returncode:raise RuntimeError("Family publisher blocked exact PlantNet source photo: "+res.stdout+res.stderr)
                if not check:report["published"]=json.loads(res.stdout)["installed"]
            assert report["published"]==ready
        report["cumulative_published"]=report["published"]+sum(b.get("published",0) for b in batches)
        report["held_by_reason"]=dict(collections.Counter(z.get("reason","") for z in report["records"] if z["status"]=="HELD"))
        prior_file.parent.mkdir(parents=True,exist_ok=True)
        prior_file.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("PLANTNET_HISTORICAL_SOURCE_RELEASE",json.dumps({
        "repository":a.repository,"selected":report["selected"],"installed":report["published"],
        "held":report["held"],"remaining":report["remaining_candidates"],
        "held_reasons":report["held_by_reason"]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
