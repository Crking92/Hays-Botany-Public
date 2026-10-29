#!/usr/bin/env python3
"""Read-only HTTP and pixel-decode test of existing family galleries on public Pages."""
import io,json,random,time,urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

COLLECTIONS={
 "Hays-Botany-Asteraceae":(180,162,116),
 "Hays-Botany-Fabaceae":(91,18,11),
 "Hays-Botany-Monocots-Aquatics":(113,35,23),
 "Hays-Botany-Lamiales":(102,102,55),
 "Hays-Botany-Asterid-Allies":(118,64,30),
 "Hays-Botany-Cacti-Buttercups":(107,37,25),
 "Hays-Botany-Spurges-Mallows":(130,99,48),
 "Hays-Botany-Trees-Shrubs":(133,107,51),
 "Hays-Botany-Mixed-Families":(105,19,14),
}

def read(url,attempts=3):
    for try_no in range(attempts):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"HaysBotanyPublicGallerySmoke/20261029"})
            with urllib.request.urlopen(req,timeout=30) as response:
                if response.status!=200:raise ValueError("Non-200 response")
                return response.read(),response.headers.get("Content-Type","")
        except Exception:
            if try_no+1==attempts:raise
            time.sleep(2*(try_no+1))
def img_check(item):
    repo,root,path=item
    url=root+path
    content,mime=read(url)
    if not mime.lower().startswith("image/"):raise AssertionError((repo,path,mime))
    with Image.open(io.BytesIO(content)) as im:
        im.verify()
    with Image.open(io.BytesIO(content)) as im:
        w,h=im.size
        if min(w,h)<80:raise AssertionError((repo,path,w,h))
    return (repo,len(content))
def verify(repo,expected):
    species,photos,with_photos=expected
    root="https://crking92.github.io/"+repo+"/site/"
    index=json.loads(read(root+"data/collection-index.json")[0])
    assert len(index["entries"])==species,(repo,"species mismatch")
    js=read(root+"app.js")[0].decode("utf-8")
    css=read(root+"styles.css")[0].decode("utf-8")
    assert "gallery" in js.lower() and "gallery-strip" in css,(repo,"visual gallery assets not deployed")
    if repo=="Hays-Botany-Lamiales":
        manifest=json.loads(read(root+"data/reviewed-external-photo-manifest.json")[0])
        entries=manifest["species"]
        found=sum(map(len,entries.values()))
        count_species=len(entries)
        paths=[p["src"] for group in entries.values() for p in group if p["src"].startswith("media/")]
    else:
        gallery=json.loads(read(root+"data/gallery-index.json")[0])
        found=gallery["photo_count"]
        count_species=gallery["photo_species"]
        paths=[p["first_src"] for p in gallery["entries"].values() if p["count"] and p["first_src"]]
        if repo!="Hays-Botany-Asteraceae":
            # Test every locally hosted image, not just thumbnails.
            extra=[]
            for row in index["entries"]:
                if row.get("photo_count",0):
                    card=json.loads(read(root+"data/species/"+row["id"]+".json")[0])
                    extra.extend(p["src"] for p in card["verified_photos"])
            paths=extra
        else:
            # Asteraceae includes all 153 image references; fetch every verified species card.
            extra=[]
            for row in index["entries"]:
                if gallery["entries"][row["id"]]["count"]:
                    card=json.loads(read(root+"data/species/"+row["id"]+".json")[0])
                    extra.extend(p["src"] for p in card["verified_photos"])
            paths=extra
    assert found==photos and count_species==with_photos,(repo,found,count_species,expected)
    assert len(paths)==(photos-2 if repo=="Hays-Botany-Lamiales" else photos),(repo,len(paths),photos)
    print("SITE_GALLERY_METADATA_PASS",repo,species,photos,with_photos,len(paths),flush=True)
    return root,paths

def main():
    everything=[]
    for repo,expected in COLLECTIONS.items():
        root,paths=verify(repo,expected)
        everything.extend((repo,root,p) for p in paths)
    with ThreadPoolExecutor(max_workers=12) as workers:
        rows=list(workers.map(img_check,everything))
    bytes_read=sum(n for _,n in rows)
    assert len(rows)==641,(len(rows),bytes_read)
    print("ALL_EXISTING_FAMILY_GALLERIES_LIVE_PASS",json.dumps({
        "family_websites":len(COLLECTIONS),
        "species_indexed":sum(a for a,_,_ in COLLECTIONS.values()),
        "approved_photos":sum(b for _,b,_ in COLLECTIONS.values()),
        "public_images_loaded_and_decoded":len(rows),
        "commons_remote_links_excluded_from_byte_check":2,
        "bytes_decoded":bytes_read,
        "original_learner_modified":False,"new_photos_collected":0
    },sort_keys=True),flush=True)
if __name__=="__main__":main()
