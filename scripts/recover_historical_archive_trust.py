#!/usr/bin/env python3
"""Bulk retry of archived, previously reviewed Commons source holds across family sites.

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
def canonical_cc_url(raw:str)->str:
    """Fix standard CC deed translations but NEVER erase country-specific porting."""
    p=urllib.parse.urlsplit(stripped(raw).strip().replace("http://","https://"))
    if p.scheme!="https" or p.netloc.lower()!="creativecommons.org":return ""
    path=p.path.rstrip("/")
    if path.endswith("/deed.en"):
        path=path[:-len("/deed.en")]
    else:
        path=re.sub(r"/deed\.[a-z]{2}$","",path,flags=re.I)
    license_path=re.fullmatch(r"/licenses/(by|by-sa|by-nc|by-nc-sa)/(2\.0|3\.0|4\.0)",path,flags=re.I)
    if license_path:
        x,v=license_path.groups()
        return f"https://creativecommons.org/licenses/{x.lower()}/{v}/"
    if path=="/publicdomain/zero/1.0":
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    return ""

def claim_license(claim:str)->tuple[str,str]:
    """Only exact individually recorded license + version, never a generic or assumed license."""
    c=re.sub(r"\s+"," ",str(claim or "").strip().upper())
    if c=="CC0 1.0":return PHOTO_CODES["cc0"]
    m=re.fullmatch(r"CC (BY|BY-SA|BY-NC|BY-NC-SA) (2\.0|3\.0|4\.0)",c)
    if not m:raise RuntimeError("Archived individual license has unsupported or unspecified version: "+c[:75])
    kind,version=m.groups()
    url=f"https://creativecommons.org/licenses/{kind.lower()}/{version}/"
    if url not in KNOWN_LICENSE_URLS:
        raise RuntimeError("No publisher-compatible named license for "+c)
    return KNOWN_LICENSE_URLS[url]

def exact_commons_media_url(page:str,direct:str)->str:
    """Require a genuine Commons File: page and its exact uploaded media filename."""
    raw=urllib.parse.urlsplit(page);u=urllib.parse.urlsplit(direct)
    if raw.scheme!="https" or raw.netloc.lower()!="commons.wikimedia.org" or not raw.path.startswith("/wiki/File:"):
        raise RuntimeError("Historical source was not the exact Commons File page")
    if u.scheme!="https" or u.netloc.lower() not in ("upload.wikimedia.org","thumb.wikimedia.org","commons.wikimedia.org"):
        raise RuntimeError("Historical image URL not on verified Wikimedia media host")
    if u.netloc.lower()=="commons.wikimedia.org" and not u.path.startswith("/wiki/Special:Redirect/file/"):
        raise RuntimeError("Wikimedia image URL is not an exact file redirect")
    filename=urllib.parse.unquote(raw.path.split("/wiki/File:",1)[1]).replace(" ","_")
    media_path=urllib.parse.unquote(u.path).replace(" ","_")
    if filename not in media_path:
        raise RuntimeError("Exact Commons file page name does not match historic direct media URL")
    return direct

def archive_verified_commons_fallback(c:dict,prior_problem:str)->dict:
    """Prior per-file review + exact archived bytes + current direct-photo fingerprint.

    The source API's 429 is NOT evidence of a new license. We rely on the exact
    previously authored image-sources.csv license record, not a generic taxon license.
    A failed image comparison, unknown author or unversioned license stays held.
    """
    name,url=claim_license(c.get("claimed_license"))
    creator=creator_display(c.get("claimed_creator"))
    if not creator or not creator_matches(creator,creator):
        raise RuntimeError("Historical Commons photographer unconfirmed")
    direct=c.get("direct_url") or c.get("direct_image_url") or ""
    direct=exact_commons_media_url(c.get("source_page") or "",direct)
    distance=(dhash(c["original_bytes"])^dhash(request(direct))).bit_count()
    if distance>12:raise RuntimeError("Historical media is not the exact linked Commons photograph: "+str(distance))
    return {"license":name,"license_url":url,"creator":creator,
       "exact_page":c["source_page"],"taxon":c["scientific_name"],
       "source_type":"commons","source_id":c["source_page"],
       "evidence":"Reused individually authored archival source CSV for this precise Commons File page, "
          "with photographer "+creator+", recorded "+name+", unchanged source archive SHA "
          +c["git_blob_sha"]+" and direct Wikimedia media fingerprint distance "+str(distance)
          +"; external Commons imageinfo could not be read: "+prior_problem[:100]}

# Use the existing actual family-site publisher whitelist. A previous
# photo-level CSV record is not enough if the license is unversioned, VRT-only,
# ARR, ND, or has an unsupported jurisdiction. Do NOT silently relicense.
ARCHIVE_REUSE_LICENSES={
    "CC0 1.0":"https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 2.0":"https://creativecommons.org/licenses/by/2.0/",
    "CC BY 3.0":"https://creativecommons.org/licenses/by/3.0/",
    "CC BY 4.0":"https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 2.0":"https://creativecommons.org/licenses/by-sa/2.0/",
    "CC BY-SA 2.0 FR":"https://creativecommons.org/licenses/by-sa/2.0/fr/",
    "CC BY-SA 3.0":"https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0":"https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-NC 4.0":"https://creativecommons.org/licenses/by-nc/4.0/",
    "CC BY-NC-SA 4.0":"https://creativecommons.org/licenses/by-nc-sa/4.0/",
}
def commons_verify(c:dict)->dict:
    # User authorized reuse of our own archived per-photo source/credit records.
    # The original preserved bytes are checked against the migration SHA
    # before this function is called. No Wikimedia API or invented license.
    original=str(c.get("source_page") or "").strip()
    url=urllib.parse.urlsplit(original)
    if url.scheme!="https" or url.netloc.lower()!="commons.wikimedia.org" or not url.path.startswith("/wiki/File:"):
        raise RuntimeError("Exact historic Commons File page missing")
    filename=urllib.parse.unquote(url.path.split("/wiki/File:",1)[1]).strip()
    if not filename or "." not in filename or len(filename)<7:
        raise RuntimeError("Archived Commons source lacks exact image filename")
    archived_license=str(c.get("claimed_license") or "").strip().upper()
    if archived_license not in ARCHIVE_REUSE_LICENSES:
        raise RuntimeError("Archived per-photo rights unverified or unsupported: "+archived_license[:95])
    creator=creator_display(c.get("claimed_creator"))
    if not creator or not creator_matches(creator,creator):
        raise RuntimeError("Archived individual photo photographer is missing or vague")
    old_reuse=str(c.get("public_reuse") or "").lower()
    if any(x in old_reuse for x in ("not for public","all rights reserved","permission required","private only","no redistribution")):
        raise RuntimeError("Original per-photo archive limits public redistribution")
    # Require a photo-specific original source URL, not a genus or species page.
    # If a matching direct media URL was captured, cross-check its filename.
    direct=str(c.get("direct_url") or c.get("direct_image_url") or "").strip()
    if direct:
        d=urllib.parse.urlsplit(direct)
        if d.scheme!="https" or d.netloc.lower() not in (
          "upload.wikimedia.org","commons.wikimedia.org","thumb.wikimedia.org"):
            raise RuntimeError("Archived direct photo URL not on a trusted Wikimedia host")
        if d.netloc.lower()=="commons.wikimedia.org" and not (
          d.path.startswith("/wiki/Special:Redirect/file/") or d.path.startswith("/w/index.php")):
            raise RuntimeError("Archived Commons media URL is not an exact file redirect")
        import os
        from_page=re.sub(r"[^a-z0-9]","",filename.lower())
        from_direct=re.sub(r"[^a-z0-9]","",urllib.parse.unquote(d.path).lower())
        if len(from_page)>10 and from_page not in from_direct:
            raise RuntimeError("Historic direct photo media URL does not match exact Commons file page")
    return {"license":archived_license,
      "license_url":ARCHIVE_REUSE_LICENSES[archived_license],
      "creator":creator,"exact_page":original,
      "taxon":c["scientific_name"],"source_type":"commons","source_id":original,
      "evidence":"Existing historical image-sources.csv entry for exact Commons photo "
        +filename+"; original individual photographer "+creator
        +"; archived specific reuse license "+archived_license
        +"; preserved photo byte SHA checked against original transfer manifest "
        +c["git_blob_sha"]
        +"; reused under owner's previously recorded photo-rights approval policy; "
        +"no new online Commons license assertion"}

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
    # This ledger never changes the earlier decisions; repeat only safe error classes.
    history=json.loads((site.parent/"workflow"/"multi-family-historical-recovery-2026-11-03.json").read_text())
    all_prior=[r for b in (history.get("previous_batches") or [])+[history]
               for r in b.get("records",[])]
    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}
    report_path=site.parent/"workflow"/"multi-family-historical-archive-trust-2026-11-03.json"
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
    processed_before={r.get("git_blob_sha") for b in previous_batches
                      for r in b.get("records",[]) if r.get("git_blob_sha")}
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
        if sh not in eligible_held:
            omitted["outside_reviewed_commons_recovery_lane"]+=1
            continue
        if sh in processed_before:
            omitted["reviewed_in_previous_bulk_pass"]+=1
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
           "direct_image_url":row.get("direct_image_url") or "", "public_reuse":row.get("public_reuse") or "",
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
       "repository":a.repository,"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03",
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
    print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({
      "repository":a.repository,"source_files":report["source_files"],
      "source_identified_candidates":report["candidate_pool_with_usable_source_identifiers"],
      "selected":report["selected_candidates"],"installed":report["new_installed"],
      "held":report["held_checked"],"duplicates":report["duplicates_found_during_review"],
      "remaining_source_candidates":report["remaining_candidates_not_yet_checked"],
      "reasons":report["held_by_reason"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
