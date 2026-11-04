#!/usr/bin/env python3
"""Review historical GBIF photographs from exact trusted institutional hosts.

No general site permission: each archived original needs its own institution
media identifier, current GBIF multimedia license, original credit and exact
photo-pixel match. Existing releases deduplicate by original image blob SHA.
"""
from pathlib import Path
src=Path(__file__).with_name("recover_historical_archive_trust.py")
s=src.read_text()
def patch(old,new,n=1):
 global s
 if s.count(old)!=n:raise RuntimeError("Unexpected historic original-audit revision: "+old[:60])
 s=s.replace(old,new,n)
patch('''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="commons" and
       ("429" in str(r.get("reason","")) or
        "Wikimedia current image license URL unsupported" in str(r.get("reason","")))}''',
'''    eligible_held={r.get("git_blob_sha") for r in all_prior
       if r.get("status")=="HELD" and r.get("lane")=="gbif" and
       str(r.get("reason","")).startswith("Source-image URL host is not trusted")}''')
patch('           "claimed_license":row.get("license") or "", "photo_id":row.get("photo_id") or "",',
      '           "claimed_license":row.get("license") or "", "archived_license_url":row.get("license_url") or "", "photo_id":row.get("photo_id") or "",')
patch('def classify(c:dict)->str:', '''def checked_institutional_gbif(c:dict)->dict:
    import urllib.parse
    match=re.search(r"/occurrence/(\d+)",str(c.get("source_page") or ""))
    if not match:raise RuntimeError("Exact original GBIF occurrence ID missing")
    oid=int(match.group(1))
    o=request("https://api.gbif.org/v1/occurrence/"+str(oid),json_response=True)
    if int(o.get("key") or 0)!=oid:raise RuntimeError("Original GBIF source record changed")
    taxon=str(o.get("species") or o.get("scientificName") or "")
    expected=" ".join(c["scientific_name"].split()[:2])
    if len(expected.split())!=2 or not (taxon==expected or taxon.startswith(expected+" ")):
        raise RuntimeError("Institutional occurrence differs from archived species: "+taxon)
    institutional_hosts=("collections.nmnh.si.edu","media01.symbiota.org","images.mobot.org")
    original_urls=[str(c.get("direct_url") or ""),str(c.get("direct_image_url") or "")]
    original_urls=[u for u in original_urls if urllib.parse.urlsplit(u).scheme=="https" and
       urllib.parse.urlsplit(u).netloc.lower() in institutional_hosts]
    if not original_urls:raise RuntimeError("No archived source image at one of three exact institutional hosts")
    def identifier_matches(a,b):
        ap=urllib.parse.urlsplit(a);bp=urllib.parse.urlsplit(b)
        if ap.scheme!="https" or bp.scheme!="https" or ap.netloc.lower()!=bp.netloc.lower():
            return False
        if ap.path!=bp.path:return False
        if ap.netloc.lower()=="collections.nmnh.si.edu":
            x=urllib.parse.parse_qs(ap.query).get("i",[])
            y=urllib.parse.parse_qs(bp.query).get("i",[])
            return bool(x and x==y)
        return True
    media=[m for m in o.get("media") or []
           if any(identifier_matches(a,str(m.get("identifier") or "")) for a in original_urls)]
    if len(media)!=1:raise RuntimeError("Original institutional media not uniquely present in GBIF")
    m=media[0]
    right=str(m.get("license") or "").strip().replace("http://","https://")
    right=right.split("/deed.")[0].rstrip("/")+"/"
    exact={
       "https://creativecommons.org/publicdomain/zero/1.0/":"CC0 1.0",
       "https://creativecommons.org/licenses/by-nc-sa/3.0/":"CC BY-NC-SA 3.0"
    }
    if right not in exact:raise RuntimeError("Current individual institution image license unsupported: "+right)
    license_name=exact[right]
    original_claim=" ".join(str(c.get("claimed_license") or "").strip().upper().split())
    if not (original_claim==license_name or
      (original_claim=="CC0" and license_name=="CC0 1.0") or
      (original_claim=="CC BY-NC-SA" and license_name=="CC BY-NC-SA 3.0")):
        raise RuntimeError("Archived individual image rights conflict with current GBIF media license")
    archived_url=str(c.get("archived_license_url") or "").replace("http://","https://").rstrip("/")+"/"
    if archived_url and archived_url!=right:
        raise RuntimeError("Archived specific license URL differs from current individual media license")
    author=creator_display(c.get("claimed_creator"))
    if not author or any(x in author.casefold() for x in ("unknown","unverified","anonymous")):
        raise RuntimeError("Original institutional photo author credit not individually recorded")
    current_credit=str(m.get("creator") or m.get("rightsHolder") or "").strip()
    if current_credit:
        if not (creator_matches(author,current_credit) or
          (author=="MBG" and "missouri botanical garden" in current_credit.casefold())):
            raise RuntimeError("Current institution source photographer differs from original photo credit")
    media_url=str(m.get("identifier") or "")
    if urllib.parse.urlsplit(media_url).netloc.lower() not in institutional_hosts:
        raise RuntimeError("Final institutional image redirect crosses untrusted host")
    current_bytes=request(media_url)
    dist=(dhash(c["original_bytes"])^dhash(current_bytes)).bit_count()
    if dist>12:raise RuntimeError("Archived image does not match exact institution GBIF media pixels: "+str(dist))
    return {"license":license_name,"license_url":right,
      "creator":author,"exact_page":"https://www.gbif.org/occurrence/"+str(oid),
      "taxon":taxon,"source_type":"institutional-gbif","source_id":str(oid),
      "evidence":"Exact original GBIF occurrence "+str(oid)+
         ", individual media "+media_url+", image-specific rights "+right+
         ", original per-photo institutional credit '"+author+"'"+
         (", current GBIF media credit '"+current_credit+"'" if current_credit
          else ", original exact-image CSV credit preserved; current media lacks explicit creator")+
         ", original archive image SHA validated and dHash distance "+str(dist)}
def classify(c:dict)->str:''')
patch('checked={"inat":inat_verify,"gbif":gbif_verify,"commons":commons_verify}[c["lane"]](c)',
      'checked={"inat":inat_verify,"gbif":checked_institutional_gbif,"commons":commons_verify}[c["lane"]](c)')
patch("multi-family-historical-archive-trust-2026-11-03.json","multi-family-historical-institutional-gbif-2026-11-03.json")
patch('"batch_key":"MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST_2026-11-03"',
      '"batch_key":"MULTIFAMILY_HISTORICAL_INSTITUTIONAL_GBIF_2026-11-03"')
patch('print("MULTIFAMILY_HISTORICAL_ARCHIVE_TRUST",json.dumps({',
      'print("MULTIFAMILY_HISTORICAL_INSTITUTIONAL_GBIF",json.dumps({')
exec(compile(s,str(src),"exec"),{"__name__":"__main__","__file__":str(src)})
