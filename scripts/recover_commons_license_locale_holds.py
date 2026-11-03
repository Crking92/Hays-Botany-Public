#!/usr/bin/env python3
"""Targeted review of held Commons photos with localized Creative Commons URLs.

This runs INSIDE each assigned public family repository. Never copies a hold
automatically: inspect source CSV, original archive image Git blob, *current*
exact-photo license and photographer, credible taxon identity, and matching
image pixels. Only verified images are given to the family's existing
rights-gated publisher; all other source bytes remain in the archive.

Supported first-pass source types: exact iNaturalist observation/photo,
GBIF occurrence with exact media, and Commons File with current imageinfo.
No license inference from a species, taxon-page image or iNaturalist account.
"""
from __future__ import annotations
import argparse, collections, csv, datetime, hashlib, html, io, json
import re, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

IMG_EXT={".jpg",".jpeg",".png",".webp"}
PHOTO_CODES={
    "cc0":("CC0 1.0","https://creativecommons.org/publicdomain/zero/1.0/"),
    "cc-by":("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/"),
    "cc-by-sa":("CC BY-SA 4.0","https://creativecommons.org/licenses/by-sa/4.0/"),
    "cc-by-nc":("CC BY-NC 4.0","https://creativecommons.org/licenses/by-nc/4.0/"),
    "cc-by-nc-sa":("CC BY-NC-SA 4.0","https://creativecommons.org/licenses/by-nc-sa/4.0/"),
}
KNOWN_LICENSE_URLS={}
for kind in ("by","by-sa","by-nc","by-nc-sa"):
    for ver in ("2.0","3.0","4.0"):
        KNOWN_LICENSE_URLS[f"https://creativecommons.org/licenses/{kind}/{ver}/"]=(f"CC {kind.upper().replace('-','-')} {ver}",f"https://creativecommons.org/licenses/{kind}/{ver}/")
KNOWN_LICENSE_URLS["https://creativecommons.org/publicdomain/zero/1.0/"]=PHOTO_CODES["cc0"]
SOURCE_IMAGE_HOSTS=("inaturalist-open-data.s3.amazonaws.com","static.inaturalist.org","upload.wikimedia.org")
USER_AGENT="Hays-Botany-Historical-CrossFamily/2026-11-03 (+educational photo-license auditing)"

def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def request(url:str,*,json_response=False)->bytes|dict:
    if not url.startswith("https://"):
        raise ValueError("Source URL is not HTTPS")
    last=None
    for t in range(2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json" if json_response else "image/*"})
            with urllib.request.urlopen(req,timeout=22) as resp:
                if resp.status!=200:raise RuntimeError("HTTP "+str(resp.status))
                data=resp.read(20*1024*1024)
                return json.loads(data) if json_response else data
        except Exception as err:
            last=err;time.sleep(1+t*2)
    raise RuntimeError("Source unavailable: "+str(last)[:170])
def stripped(s:str)->str:
    return html.unescape(re.sub(r"<[^>]*>"," ",str(s or ""))).replace("\u00a0"," ")
def creator_display(s:str)->str:
    s=stripped(s).strip()
    s=re.sub(r"^(?:\(c\)|©)\s*","",s,flags=re.I)
    s=re.split(r",?\s*(?:some rights reserved|no rights reserved|uploaded by)\b",s,flags=re.I)[0]
    s=re.sub(r"\([^)]*CC BY[^)]*\)","",s,flags=re.I)
    return re.sub(r"\s+"," ",s).strip(" ,-.;")
def creator_matches(claimed:str,actual:str)->bool:
    a=creator_display(claimed).casefold();b=creator_display(actual).casefold()
    if not a or not b:return False
    vague=("inat observer","inat user","license","source unknown","unknown","photographer","copyright","contributor","wikipedia","wikimedia")
    if any(t in a for t in vague):return False
    return a in b or b in a or (
        len(a)>=6 and a.replace(" ", "") in b.replace(" ",""))
def dhash(data:bytes)->int:
    with Image.open(io.BytesIO(data)) as im:
        if im.width*im.height>80000000:raise RuntimeError("Image pixel limit exceeded")
        a=list(ImageOps.exif_transpose(im).convert("L").resize((9,8),Image.Resampling.LANCZOS).getdata())
    return sum(1<<i for i in range(64) if a[(i//8)*9+i%8]>a[(i//8)*9+i%8+1])
def collect_photo_url(url:str,photo_id:int|None=None)->str:
    parsed=urllib.parse.urlparse(str(url or ""))
    if parsed.scheme!="https" or parsed.netloc not in SOURCE_IMAGE_HOSTS:
        raise RuntimeError("Source-image URL host is not trusted")
    if photo_id is not None and f"/photos/{photo_id}/" not in parsed.path:
        raise RuntimeError("Source media path does not identify the exact photo")
    return url
def lic_norm(s:str)->str|None:
    s=str(s or "").lower().replace("_","-").replace(" ","-")
    if "by-nc-nd" in s or "by-nd" in s:return None
    if s in PHOTO_CODES:return s
    if s.startswith("https://creativecommons.org/") or s.startswith("http://creativecommons.org/"):
        s=s.replace("http://","https://")
        return KNOWN_LICENSE_URLS.get(s.rstrip("/")+"/")
    return None
def validate_claim(claim:str,current:str,*,commons=False)->None:
    claim=str(claim or "").lower().replace(" ","-")
    if "all-rights" in claim or "private-study-only" in claim or "not-cleared" in claim or "-nd" in claim:
        raise RuntimeError("Archived photo carries a restrictive/uncleared license statement")
    if commons:
        return
    if any(k in claim for k in ("cc-by","cc0")):
        if "nc-sa" in claim and current!="cc-by-nc-sa":raise RuntimeError("Archived NC-SA claimed license conflicts with current photo")
        if "by-nc" in claim and current not in ("cc-by-nc","cc-by-nc-sa","cc-by","cc-by-sa","cc0"):
            raise RuntimeError("Archived NC claimed license conflicts with current photo")
        if "by-sa" in claim and current not in ("cc-by-sa","cc-by-nc-sa","cc0"):
            raise RuntimeError("Archived SA claimed license conflicts with current photo")
def inat_verify(c:dict)->dict:
    observation=int(c["observation_id"])
    photo_id=int(c["photo_id"])
    data=request(f"https://api.inaturalist.org/v1/observations/{observation}",json_response=True)
    matches=data.get("results") or []
    if len(matches)!=1 or matches[0].get("id")!=observation:raise RuntimeError("Original observation ID not found")
    obs=matches[0]
    taxon=(obs.get("taxon") or {}).get("name") or ""
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("Taxon mismatch: "+taxon+" vs "+expected)
    photos=[p for p in (obs.get("photos") or []) if p.get("id")==photo_id]
    if len(photos)!=1:raise RuntimeError("Exact photo absent from original observation")
    p=photos[0];code=p.get("license_code")
    if code not in PHOTO_CODES:raise RuntimeError("Photo-specific current iNaturalist license unsupported: "+str(code))
    validate_claim(c.get("claimed_license"),code)
    attribution=p.get("attribution") or ""
    if not creator_matches(c.get("claimed_creator"),attribution):
        raise RuntimeError("Current photo creator differs from original image CSV: "+str(attribution)[:140])
    image_urls=[c.get("direct_url"),c.get("direct_image_url"),p.get("large_url"),
        re.sub(r"/(?:square|medium|small|thumb)\.", "/large.",str(p.get("url") or "")),p.get("url")]
    attempts=[]
    for u in dict.fromkeys(str(u) for u in image_urls if u):
        try:
            u=collect_photo_url(u,photo_id)
            distance=(dhash(c["original_bytes"])^dhash(request(u))).bit_count()
            attempts.append((distance,u))
            if distance<=12:break
        except Exception:
            continue
    if not attempts:raise RuntimeError("No accessible exact-photo image to compare")
    dist,ident=min(attempts,key=lambda pair:pair[0])
    if dist>12:raise RuntimeError("Original differs from current individual-photo pixels: "+str(dist))
    return {"license":PHOTO_CODES[code][0],"license_url":PHOTO_CODES[code][1],
            "creator":creator_display(attribution),"exact_page":f"https://www.inaturalist.org/photos/{photo_id}",
            "taxon":taxon,"source_type":"inat","source_id":str(observation),
            "evidence":"iNaturalist observation "+str(observation)+" photo "+str(photo_id)+
              " individual CC code "+code+"; photographer "+attribution+"; image dHash difference "+str(dist)}
def gbif_verify(c:dict)->dict:
    match=re.search(r"/occurrence/(\d+)",c.get("source_page") or "")
    if not match:raise RuntimeError("GBIF occurrence source URL missing")
    oid=int(match.group(1))
    o=request("https://api.gbif.org/v1/occurrence/"+str(oid),json_response=True)
    taxon=o.get("species") or o.get("scientificName") or ""
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("GBIF source species differs: "+taxon+" vs "+expected)
    target_urls=[str(c.get("direct_image_url") or ""),str(c.get("direct_url") or "")]
    pid=re.search(r"/photos/(\d+)/", " ".join(target_urls))
    photo_id=int(pid.group(1)) if pid else None
    ms=[]
    for m in o.get("media") or []:
        ident=str(m.get("identifier") or "")
        if (ident in target_urls and ident) or (photo_id and f"/photos/{photo_id}/" in ident):
            ms.append(m)
    if len(ms)!=1:raise RuntimeError("Exact archived media identifier not uniquely located in GBIF occurrence")
    m=ms[0]
    license_url=str(m.get("license") or "").replace("http://","https://").rstrip("/")+"/"
    if license_url not in KNOWN_LICENSE_URLS:raise RuntimeError("Unsupported GBIF individual media license "+license_url)
    license_name,license_url=KNOWN_LICENSE_URLS[license_url]
    source_person=m.get("creator") or m.get("rightsHolder") or ""
    if not creator_matches(c.get("claimed_creator"),source_person):
        raise RuntimeError("GBIF individual media photographer not confirmed: "+str(source_person))
    url=str(m.get("identifier") or "")
    url=collect_photo_url(url,photo_id) if photo_id else collect_photo_url(url)
    dist=(dhash(c["original_bytes"])^dhash(request(url))).bit_count()
    if dist>12:raise RuntimeError("Original does not match exact GBIF media pixels: "+str(dist))
    page=f"https://www.inaturalist.org/photos/{photo_id}" if photo_id else "https://www.gbif.org/occurrence/"+str(oid)
    return {"license":license_name,"license_url":license_url,"creator":creator_display(source_person),
            "exact_page":page,"taxon":taxon,"source_type":"gbif","source_id":str(oid),
            "evidence":"GBIF occurrence "+str(oid)+" exact image "+url+"; image-level license "+
             license_url+"; creator "+source_person+"; dHash distance "+str(dist)}
def canonical_commons_cc_url(raw:str)->str:
    """Canonicalize only genuine Creative Commons license URLs with locale/deed tails."""
    parsed=urllib.parse.urlsplit(stripped(raw).strip().replace("http://","https://"))
    if parsed.scheme!="https" or parsed.netloc.lower()!="creativecommons.org":
        return ""
    p=parsed.path.rstrip("/")
    m=re.fullmatch(r"/licenses/(by|by-sa|by-nc|by-nc-sa)/(2\.0|3\.0|4\.0)(?:/[a-z]{2}(?:-[a-z]{2})?)?(?:/deed(?:\.[a-z]{2})?)?",p,flags=re.I)
    if m:
        kind,version=m.groups()
        return f"https://creativecommons.org/licenses/{kind.lower()}/{version}/"
    if re.fullmatch(r"/publicdomain/zero/1\.0(?:/[a-z]{2}(?:-[a-z]{2})?)?(?:/deed(?:\.[a-z]{2})?)?",p,flags=re.I):
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    return ""

DIRECT_FILE_RIGHTS={
    # Individual Commons file source, contributor, CC0 bot review, and original media
    # independently read on 2026-11-03. This entry is never a blanket taxon license.
    "7f181fae4d5c533e6dc2010e953239a60e950735":{
        "page":"https://commons.wikimedia.org/wiki/File:Polytaenia_texana_-_Texas_Prairie_Parsley.jpg",
        "creator":"Ben Clement",
        "license":"CC0 1.0",
        "license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
        "url":"https://upload.wikimedia.org/wikipedia/commons/c/cc/Polytaenia_texana_-_Texas_Prairie_Parsley.jpg",
        "taxon":"Polytaenia texana"
    }
}
def independently_verified_commons(c:dict)->dict|None:
    e=DIRECT_FILE_RIGHTS.get(c.get("git_blob_sha"))
    if not e:return None
    if c.get("source_page")!=e["page"]:
        raise RuntimeError("Archived per-photo Commons page not identical to independently verified file")
    if not creator_matches(c.get("claimed_creator"),e["creator"]):
        raise RuntimeError("Photographer inconsistent with original per-photo archive metadata")
    if c.get("scientific_name")!=e["taxon"]:
        raise RuntimeError("Original taxon and file's verified species differ")
    if c.get("claimed_license")!=e["license"]:
        raise RuntimeError("Archive license statement differs from independently checked file license")
    if e["license"]!="CC0 1.0" or e["license_url"]!="https://creativecommons.org/publicdomain/zero/1.0/":
        raise RuntimeError("Direct-file rights entry has an unsupported license")
    image_url=collect_photo_url(e["url"])
    dist=(dhash(c["original_bytes"])^dhash(request(image_url))).bit_count()
    if dist>12:
        raise RuntimeError("Archived original photo does not match the exact independently licensed file")
    return {"license":e["license"],"license_url":e["license_url"],"creator":e["creator"],
            "exact_page":e["page"],"taxon":e["taxon"],"source_type":"commons",
            "source_id":e["page"],
            "evidence":"Exact Commons file page, CC0 bot review, credited photographer and direct media independently examined 2026-11-03; original image dHash distance "+str(dist)}

def commons_verify(c:dict)->dict:
    directly_checked=independently_verified_commons(c)
    if directly_checked is not None:return directly_checked
    original=c.get("source_page") or ""
    m=re.search(r"commons\.wikimedia\.org/wiki/File:(.+)",original)
    if not m:raise RuntimeError("No exact Wikimedia Commons File: source")
    title="File:"+urllib.parse.unquote(m.group(1)).replace("_"," ")
    query=urllib.parse.urlencode({"action":"query","prop":"imageinfo","iiprop":"url|extmetadata","titles":title,"format":"json"})
    doc=request("https://commons.wikimedia.org/w/api.php?"+query,json_response=True)
    pages=((doc.get("query") or {}).get("pages") or {})
    infos=[i for v in pages.values() for i in v.get("imageinfo",[])]
    if len(infos)!=1:raise RuntimeError("Commons exact image info unavailable")
    info=infos[0];ext=info.get("extmetadata") or {}
    def value(k):return str((ext.get(k) or {}).get("value") or "")
    lic=canonical_commons_cc_url(value("LicenseUrl"))
    if lic not in KNOWN_LICENSE_URLS:
        raise RuntimeError("Wikimedia current image license URL unsupported "+lic)
    name,license_url=KNOWN_LICENSE_URLS[lic]
    author=stripped(value("Artist")).strip()
    if not creator_matches(c.get("claimed_creator"),author):
        raise RuntimeError("Wikimedia original author not individually confirmed "+author[:120])
    u=collect_photo_url(info.get("url") or "")
    dist=(dhash(c["original_bytes"])^dhash(request(u))).bit_count()
    if dist>12:raise RuntimeError("Original does not match the current Commons file: "+str(dist))
    return {"license":name,"license_url":license_url,"creator":creator_display(author),
            "exact_page":original,"taxon":c["scientific_name"],"source_type":"commons","source_id":title,
            "evidence":"Wikimedia Commons exact file "+title+" imageinfo license "+lic+
                       "; image-specific Artist "+author[:150]+"; image dHash distance "+str(dist)}
def classify(c:dict)->str:
    page=c.get("source_page") or ""
    if "inaturalist.org/photos/" in page and c.get("photo_id") and c.get("observation_id"):return "inat"
    if "gbif.org/occurrence/" in page:return "gbif"
    if "commons.wikimedia.org/wiki/File:" in page:return "commons"
    return "unverifiable"
def read_csv_rows(path:Path)->dict:
    if not path.is_file():return {}
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        return {r.get("file_name"):r for r in csv.DictReader(f) if r.get("file_name")}
def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",required=True,type=Path)
    p.add_argument("--site-root",required=True,type=Path)
    p.add_argument("--repository",required=True)
    p.add_argument("--limit",type=int,default=55)
    p.add_argument("--publisher",choices=("family","lamiales"),default="family")
    p.add_argument("--audit-only",action="store_true")
    a=p.parse_args()
    src=a.source_root.resolve();site=a.site_root.resolve()
    assert a.limit>0 and a.limit<=100
    config=json.loads((site/"data/collection-meta.json").read_text())
    assert config["repository_full_name"]==a.repository
    assert config.get("photo_license_policy",{}).get("noncommercial_educational_use") is True
    transfer=json.loads((src/"migration/original-source-transfer-manifest.json").read_text())
    assert transfer["summary"]["repository"]==a.repository
    archive=(src/"migration/private-original-photo-holds").resolve()
    assert archive.is_dir()
    index=json.loads((site/"data/collection-index.json").read_text())
    assigned={entry["id"]:entry for entry in index["entries"]}
    assert len(assigned)==len(index["entries"])
    # Resume across batches without repeating unresolved photo holds or losing their reasons.
    report_path=site.parent/"workflow"/"multi-family-commons-license-locale-recovery-2026-11-03.json"
    previous=json.loads(report_path.read_text()) if report_path.is_file() else {}
    previous_batches=list(previous.get("previous_batches") or [])
    if previous.get("records") is not None:
        previous_batches.append({
            "checked_at":previous.get("checked_at"),
            "selected_candidates":previous.get("selected_candidates",0),
            "new_installed":previous.get("new_installed",0),
            "held_checked":previous.get("held_checked",0),
            "records":previous.get("records",[])
        })
    historical=json.loads((site.parent/"workflow"/"multi-family-historical-recovery-2026-11-03.json").read_text())
    prior_records=[r for batch in (historical.get("previous_batches") or [])+[historical]
                   for r in batch.get("records",[])]
    previously_held={r.get("git_blob_sha") for r in prior_records if
        r.get("status")=="HELD" and
        "Wikimedia current image license URL unsupported" in str(r.get("reason",""))}
    previously_checked={r.get("git_blob_sha") for batch in previous_batches
                        for r in batch.get("records",[]) if r.get("git_blob_sha")}

    sha_published=set()
    for q in (site/"media").rglob("*"):
        if q.is_file() and q.suffix.lower() in IMG_EXT:
            sha_published.add(blob_sha(q.read_bytes()))
    csv_cache={}
    all_candidates=[];omitted=collections.Counter()
    for record in transfer["files"]:
        if record.get("class")!="PRIVATE_MEDIA_HOLD":continue
        original_path=record["source_path"]
        parts=Path(original_path).parts
        if len(parts)<7 or parts[0:2]!=("content","taxa") or parts[-2]!="images":
            omitted["original_path_shape_unknown"]+=1;continue
        family=parts[2];sid=parts[-3];fn=parts[-1]
        if Path(fn).suffix.lower() not in IMG_EXT:omitted["unsupported_image_format"]+=1;continue
        if sid not in assigned or assigned[sid]["family"]!=family:
            omitted["species_not_on_assigned_site"]+=1;continue
        file=src/record["destination"]
        if not file.resolve().is_relative_to(archive):
            omitted["historical_image_not_in_hold_archive"]+=1;continue
        if not file.is_file():
            omitted["historical_original_missing"]+=1;continue
        # Hash comes from migration's original source tree snapshot.
        sh=str(record["git_blob_sha"])
        if sh not in previously_held or sh in previously_checked:
            omitted["outside_new_locale_retry_or_previously_checked"]+=1
            continue
        if sh in sha_published:
            omitted["already_public_identical_bytes"]+=1;continue
        parent=Path(original_path).parent.parent
        if parent not in csv_cache:
            csv_cache[parent]=read_csv_rows(src/parent/"image-sources.csv")
        row=csv_cache[parent].get(fn)
        if not row:
            omitted["no_matching_per_image_csv_row"]+=1;continue
        card_file=src/parent/"species.json"
        if not card_file.is_file():
            omitted["original_species_card_missing"]+=1;continue
        card=json.loads(card_file.read_text())
        if card.get("id")!=sid:
            omitted["original_species_card_mismatch"]+=1;continue
        candidate={
           "species_id":sid,"family":family,"scientific_name":card.get("scientific_name") or sid.replace("-"," "),
           "filename":fn,"original_path":original_path,"archive_path":str(file.relative_to(src)),
           "original_file":file,"git_blob_sha":sh,"bytes":record["bytes"],
           "source_page":row.get("source_page") or "","claimed_creator":row.get("creator") or "",
           "claimed_license":row.get("license") or "", "photo_id":row.get("photo_id") or "",
           "observation_id":row.get("observation_id") or "", "direct_url":row.get("direct_url") or "",
           "direct_image_url":row.get("direct_image_url") or "",
           "role":row.get("role") or "General botanical reference",
           "modifications":row.get("modifications") or "Historical archived photograph; no new changes."
        }
        candidate["lane"]=classify(candidate)
        if candidate["lane"]=="unverifiable":
            omitted["lacks_exact_photo_and_observation_identifiers"]+=1;continue
        all_candidates.append(candidate)
    priority={"inat":0,"gbif":1,"commons":2}
    all_candidates.sort(key=lambda x:(priority.get(x["lane"],5),x["species_id"],x["filename"]))
    selected=all_candidates[:a.limit]
    report={
       "repository":a.repository,"batch_key":"MULTIFAMILY_COMMONS_LICENSE_LOCALE_RECOVERY_2026-11-03",
       "checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "source_files":len([q for q in transfer["files"] if q.get("class")=="PRIVATE_MEDIA_HOLD"]),
       "selection_window":a.limit,"candidate_pool_with_usable_source_identifiers":len(all_candidates),
       "remaining_candidates_not_yet_checked":max(0,len(all_candidates)-len(selected)),
       "selected_candidates":len(selected),"selected_by_lane":dict(collections.Counter(x["lane"] for x in selected)),
       "skipped_or_previously_published":dict(omitted),"new_installed":0,"held_checked":0,
       "duplicates_found_during_review":0,"records":[],
       "previous_batches":previous_batches,
       "batch_number":len(previous_batches)+1
    }
    approved_shas=set(sha_published)
    with tempfile.TemporaryDirectory(prefix="hays-historical-multifamily-") as td:
        root=Path(td)
        for c in selected:
            r={k:c[k] for k in ("species_id","family","filename","original_path","archive_path","git_blob_sha","lane")}
            try:
                raw=c["original_file"].read_bytes()
                if not 200<len(raw)<25*1024*1024:raise RuntimeError("Archived image size invalid")
                if len(raw)!=c["bytes"] or blob_sha(raw)!=c["git_blob_sha"]:
                    raise RuntimeError("Archived original differs from pinned migration manifest")
                if c["git_blob_sha"] in approved_shas:
                    report["duplicates_found_during_review"]+=1
                    r["status"]="DUPLICATE_NO_INSTALL";report["records"].append(r);continue
                c["original_bytes"]=raw
                # Independently checks the actual decoded image, not just its filename.
                dhash(raw)
                checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)
                dest_name="archived-"+hashlib.sha256(raw).hexdigest()[:16]+Path(c["filename"]).suffix.lower()
                dest=root/"photo-intake"/"approved"/c["species_id"]/dest_name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(raw)
                is_nc="NC" in checked["license"]
                metadata={
                  "species_id":c["species_id"],"photo_file":dest_name,
                  "status":"APPROVED_FOR_PUBLIC_FAMILY_SITE","rights_approved_for_public":True,
                  "taxon_reviewed":True,"approval_mode":"OWNER_STANDING_PHOTO_FIRST_POLICY",
                  "policy_ref":"PHOTO_FIRST_PUBLIC_GALLERY_POLICY_2026-11-02",
                  "review_operator":"Shared 2026-11-03 Hays Botany archive, source-rights and photo-fingerprint validator",
                  "source_review_evidence":checked["evidence"]+
                     "; archived source SHA "+c["git_blob_sha"]+"; exact image source "+checked["exact_page"],
                  "taxon_review_evidence":"Original species record "+c["scientific_name"]+
                     " linked to an original image and matching current "+checked["source_type"]+
                     " photo of source taxon "+checked["taxon"]+
                     ". Basic source-backed field recognition only; no diagnostic arrow certification.",
                  "approval_note":"Owner standing photo-first policy: release after exact per-photo license, credit, source taxon, archived bytes and visual-image matching checks.",
                  "creator":checked["creator"],"source_page":checked["exact_page"],"source_page_is_exact":True,
                  "license":checked["license"],"license_url":checked["license_url"],
                  "noncommercial_site_use_confirmed":is_nc,"role":c["role"],
                  "modifications":c["modifications"],
                  "sha256":hashlib.sha256(raw).hexdigest()
                }
                dest.with_name(dest.name+".json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n")
                approved_shas.add(c["git_blob_sha"])
                r.update(status="SOURCE_VERIFIED_READY",creator=checked["creator"],license=checked["license"],
                    source_page=checked["exact_page"],taxon=checked["taxon"],
                    src="media/"+c["species_id"]+"/"+dest_name, sha256=hashlib.sha256(raw).hexdigest())
            except Exception as exc:
                r.update(status="HELD",reason=str(exc)[:350])
                report["held_checked"]+=1
            report["records"].append(r)
        to_install=sum(r["status"]=="SOURCE_VERIFIED_READY" for r in report["records"])
        if to_install and not a.audit_only:
            script=site.parent/"scripts"/("publish_approved_lamiales_photos.py" if a.publisher=="lamiales" else "publish_approved_family_photos.py")
            cmd=[sys.executable,str(script),"--source-root",str(root),"--site-root",str(site)]
            for check in (True,False):
                res=subprocess.run(cmd+(["--check"] if check else []),text=True,capture_output=True)
                if res.returncode:raise RuntimeError("EXISTING_FAMILY_PUBLISHER_REJECTED "+res.stdout+" "+res.stderr)
                if not check:report["new_installed"]=json.loads(res.stdout)["installed"]
            assert report["new_installed"]==to_install,"Actual installed count differs from verified candidates"
        report["verified_but_not_installed"]=to_install-report["new_installed"]
        report["held_by_reason"]=dict(collections.Counter(r.get("reason","") for r in report["records"] if r["status"]=="HELD"))
        report["cumulative_installed"]=report["new_installed"]+sum(b.get("new_installed",0) for b in previous_batches)
        report["cumulative_held_reviewed"]=report["held_checked"]+sum(b.get("held_checked",0) for b in previous_batches)
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("MULTIFAMILY_COMMONS_LICENSE_LOCALE_RECOVERY",json.dumps({
      "repository":a.repository,"source_files":report["source_files"],
      "source_identified_candidates":report["candidate_pool_with_usable_source_identifiers"],
      "selected":report["selected_candidates"],"installed":report["new_installed"],
      "held":report["held_checked"],"duplicates":report["duplicates_found_during_review"],
      "remaining_source_candidates":report["remaining_candidates_not_yet_checked"],
      "reasons":report["held_by_reason"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
