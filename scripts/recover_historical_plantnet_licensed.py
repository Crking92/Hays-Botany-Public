#!/usr/bin/env python3
"""Reconsider historical Pl@ntNet photos with photo-level GBIF CC BY-SA records.

Nothing is approved from the generic GBIF occurrence license. For an image to
publish, the GBIF occurrence must be from Pl@ntNet's publicly shared photos,
the EXACT GBIF media must correspond to the archived original, its individual
media rights string must say CC BY-SA, the contributor must match the archived
photo author, and the preserved picture must fingerprint-match current media.
Version handling: an explicit original per-photo CC BY-SA version is respected;
when that record is unversioned, the CC BY-SA 2.0 grant in Pl@ntNet's public
terms of use is the supporting version (with that provenance recorded).
"""
from pathlib import Path
source=Path(__file__).with_name("recover_historical_archive_trust.py")
s=source.read_text()
def patch(old,new,n=1):
 global s
 if s.count(old)!=n:raise RuntimeError("Unexpected archive-audit code version: "+old[:75])
 s=s.replace(old,new,n)
old='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}'''
new='''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="gbif" and
       str(r.get("reason","")).startswith("Unsupported GBIF individual media license ")}'''
patch(old,new)
patch("def classify(c:dict)->str:",'''def gbif_plantnet_verify(c:dict)->dict:
    import urllib.parse
    source_page=str(c.get("source_page") or "")
    match=re.search(r"^https://www\\.gbif\\.org/occurrence/(\\d+)$",source_page.rstrip("/"))
    if not match:raise RuntimeError("Original archived GBIF occurrence URL missing")
    occurrence=int(match.group(1))
    record=request("https://api.gbif.org/v1/occurrence/"+str(occurrence),json_response=True)
    if str(record.get("key") or "")!=str(occurrence):
        raise RuntimeError("Original occurrence identifier changed")
    if str(record.get("datasetKey") or "").lower()!="7a3679ef-5582-4aaa-81f0-8c2545cafc81":
        raise RuntimeError("Not the public Pl@ntNet observations image dataset")
    taxon=str(record.get("species") or record.get("scientificName") or "")
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("Original GBIF taxon differs from assigned botanical species: "+taxon)
    archived_urls=[str(c.get("direct_image_url") or ""),str(c.get("direct_url") or "")]
    archived_urls=[x for x in archived_urls if urllib.parse.urlsplit(x).netloc.lower()=="bs.plantnet.org"
        and urllib.parse.urlsplit(x).path.startswith("/image/")]
    if not archived_urls:raise RuntimeError("Not an archived exact Pl@ntNet media URL")
    media=[]
    for m in record.get("media") or []:
        u=str(m.get("identifier") or "")
        parsed=urllib.parse.urlsplit(u)
        if parsed.scheme=="https" and parsed.netloc.lower()=="bs.plantnet.org" and
            any(urllib.parse.urlsplit(a).path==parsed.path for a in archived_urls):
            media.append(m)
    if len(media)!=1:raise RuntimeError("Exact archived Pl@ntNet media not unique in GBIF record")
    image=media[0]
    rights=str(image.get("license") or "").strip()
    rights_m=re.fullmatch(r"(.+?)\\s*\\(cc-by-sa\\)",rights,flags=re.I)
    if not rights_m:raise RuntimeError("Individual image rights do not explicitly confirm CC BY-SA: "+rights[:110])
    author=str(image.get("creator") or image.get("rightsHolder") or rights_m.group(1)).strip()
    if not creator_matches(c.get("claimed_creator"),author) or not creator_matches(rights_m.group(1),author):
        raise RuntimeError("Individual image creator not confirmed against archive and media rights")
    archive_license=" ".join(str(c.get("claimed_license") or "").upper().split())
    if archive_license not in ("CC BY-SA","CC BY-SA 2.0","CC BY-SA 3.0","CC BY-SA 4.0"):
        raise RuntimeError("Original per-image archive does not confirm CC BY-SA attribution")
    version=archive_license.split()[-1] if re.fullmatch(r"CC BY-SA [234]\\.0",archive_license) else "2.0"
    licensed="CC BY-SA "+version
    licensing_url="https://creativecommons.org/licenses/by-sa/"+version+"/"
    image_url=str(image["identifier"])
    parsed=urllib.parse.urlsplit(image_url)
    if parsed.scheme!="https" or parsed.netloc.lower()!="bs.plantnet.org":
        raise RuntimeError("Original Pl@ntNet image host not trusted")
    current=request(image_url)
    diff=(dhash(c["original_bytes"])^dhash(current)).bit_count()
    if diff>12:raise RuntimeError("Original picture does not match exact GBIF media image: "+str(diff))
    creator=creator_display(author)
    evidence=("GBIF Pl@ntNet observations dataset 7a3679ef-5582-4aaa-81f0-8c2545cafc81, occurrence "+
        str(occurrence)+", specific media identifier "+image_url+" and media rights '"+rights+
        "' with creator "+creator+"; original per-photo archive claims '"+archive_license+
        "'; image fingerprint dHash distance "+str(diff)+
        "; Pl@ntNet official image attribution https://docs.plantnet.org/en/reference/data-and-image-licensing/"+
        "; Pl@ntNet user image reuse grant CC BY-SA 2.0 https://identify.plantnet.org/terms_of_use"+
        "; exactly versioned source archived when available, platform version used only if source unversioned")
    return {"license":licensed,"license_url":licensing_url,"creator":creator+" / Pl@ntNet",
        "exact_page":source_page,"taxon":taxon,"source_type":"plantnet-gbif",
        "source_id":str(occurrence),"evidence":evidence}
def classify(c:dict)->str:''')
patch('checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)',
      'checked={"inat":inat_verify,"gbif":gbif_plantnet_verify,"commons":commons_verify}[c["lane"]](c)')
patch('multi-family-historical-archive-trust-2026-11-03.json','multi-family-historical-plantnet-licensed-2026-11-03.json')
patch('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
      '"batch_key":"MULTIFAMILY_HISTORICAL_PLANTNET_LICENSED_2026-11-03"')
patch('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
      'print("MULTIFAMILY_HISTORICAL_PLANTNET_LICENSED",json.dumps({')
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
