#!/usr/bin/env python3
"""Retry one exact Argythamnia / Ditaxis synonym held only on institutional media host.
GBIF occurrence, image-specific NC license, recorded photographer and source
pixels are still individually verified by the preserved shared recovery code.
"""
from pathlib import Path
source=Path(__file__).with_name("recover_verified_taxonomic_synonym_holds.py")
s=source.read_text()
sha="654dfc8c7718b9482158d668cf5e77477676de5c"
needle='SOURCE_IMAGE_HOSTS=("inaturalist-open-data.s3.amazonaws.com","static.inaturalist.org","upload.wikimedia.org")'
assert s.count(needle)==1
s=s.replace(needle,'SOURCE_IMAGE_HOSTS=("inaturalist-open-data.s3.amazonaws.com","static.inaturalist.org","upload.wikimedia.org","intermountainbiota.org")',1)
needle='        if sh in already_done:'
assert s.count(needle)==1
s=s.replace(needle,'        if sh in already_done and sh!="654dfc8c7718b9482158d668cf5e77477676de5c":',1)
needle='        if sh not in taxon_holds or sid not in APPROVED_SYNONYMS:'
assert s.count(needle)==1
s=s.replace(needle,'        if sh not in taxon_holds or sid!="argythamnia-aphoroides" or sh!="654dfc8c7718b9482158d668cf5e77477676de5c":',1)
# Extra gate: the stored original GBIF media URL must be the exact source
# specified in the original WSU specimen image record, never a lookalike.
needle='    url=str(m.get("identifier") or "")'
assert s.count(needle)==1
s=s.replace(needle,'''    if c.get("species_id")=="argythamnia-aphoroides":
        assert str(m.get("identifier") or "")=="https://intermountainbiota.org/media/intermt/WS/00416/WS068331.JPG", "WSU preserved exact GBIF media URL mismatch"
    url=str(m.get("identifier") or "")''',1)
exec(compile(s,str(source),"exec"),{"__name__":"__main__","__file__":str(source)})
