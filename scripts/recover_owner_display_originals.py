#!/usr/bin/env python3
"""Exact-hash recovery of owner-created historical photos for display on family sites.

A null iNaturalist media license is NOT treated as Creative Commons. For the
thirteen owner-named archived originals only, verify original observation,
individual photo, recorded creator, source pixels and taxon before using
the owner's previously recorded site-specific public-display permission.
"""
from pathlib import Path

OWNER_HASHES = {
 "ebef338647610b0c1a1edfb3c5f60b67e3d8ba92",
 "22a0ac3bd51e2bef3268f3c5e48933d2e1e5cf5b",
 "b637ca453d9b370aca13c63cc3578c1759add3c4",
 "bf139dc791c567cd43dd9c76972dd8c893d458e0",
 "1f2be91e2f3499053a7c2026f7f1da7e975689c0",
 "61a9bda053f069204fa18cad9ccc0205dee5b03f",
 "14b0ae32e643656b7741e2eb81bd5598ff6c15ec",
 "49991a852203279be93d8b544fc8d516eaee508a",
 "25f0ba67f2a3cd9a12f571d78dbae41b813a4ab7",
 "6e9054f9d3dcb14f4a4cb679f730a9f3c880d75b",
 "60ee76149dedf65a30baf320f68a4f99ade1acfd",
 "80ffde56f0e3b1c729ba5808910ecacc48c74a42",
 "60af75b13458b90febb53658e94bef2838f61052",
}
RIGHTS_URL="https://github.com/Crking92/Hays-Botany-Public/blob/main/docs/GLASS_ROOT_GARDEN_PUBLIC_DISPLAY_PERMISSION_20261103.md"
source=Path(__file__).with_name("recover_historical_multi_family_photos.py")
s=source.read_text()
def sub(old,new):
 global s
 if s.count(old)!=1: raise RuntimeError("Shared validator changed at: "+old[:65])
 s=s.replace(old,new,1)

# Named site-only permission is NOT an open license and is never applied to a
# third-party photo or to one not on the original 13-SHA owner permission list.
sub('KNOWN_LICENSE_URLS={}', 'PHOTO_CODES["owner-public-display"]=("OWNER PUBLIC DISPLAY PERMISSION",RIGHTS_URL)\nKNOWN_LICENSE_URLS={}')
sub('    p=photos[0];code=p.get("license_code")',
'''    p=photos[0];code=p.get("license_code")
    if c["git_blob_sha"] in OWNER_HASHES and code is None:
        if c["claimed_creator"].strip().casefold()!="glass root garden":
            raise RuntimeError("Owner permission cannot apply to another creator")
        # The owner explicitly attests these exact originals are theirs.
        # Some historical iNaturalist photo records expose only
        # "(c) ... no rights reserved" or a username, not the display credit.
        # That is NOT a Creative Commons grant and must not override
        # the owner-controlled public-site permission or named credit.
        code="owner-public-display"''')
sub('    validate_claim(c.get("claimed_license"),code)',
    '    if code!="owner-public-display":validate_claim(c.get("claimed_license"),code)')
sub('    if not creator_matches(c.get("claimed_creator"),attribution):',
    '    if code!="owner-public-display" and not creator_matches(c.get("claimed_creator"),attribution):')
sub('"creator":creator_display(attribution),"exact_page":f"https://www.inaturalist.org/photos/{photo_id}",',
    '"creator":("Glass Root Garden" if code=="owner-public-display" else creator_display(attribution)),"exact_page":f"https://www.inaturalist.org/photos/{photo_id}",')
sub('" individual CC code "+code+"; photographer "+attribution',
    '" individual source license "+str(p.get("license_code"))+"; applicable owner site-display permission "+(RIGHTS_URL if code=="owner-public-display" else "not required")+"; photographer "+attribution')
sub('        if sh in previously_held and sh not in retry_kew_pumila:',
    '        if sh in previously_held and sh not in retry_kew_pumila and sh not in OWNER_HASHES:')
sub('        if sh in sha_published:',
'''        if sh not in OWNER_HASHES:
            omitted["outside_exact_owner_permission_list"]+=1;continue
        if sh in sha_published:''')
sub('multi-family-historical-recovery-2026-11-03.json',
    'multi-family-owner-display-recovery-2026-11-03.json')
sub('is_nc="NC" in checked["license"]',
    'is_nc=("NC" in checked["license"] or checked["license"]=="OWNER PUBLIC DISPLAY PERMISSION")')
sub('MULTIFAMILY_HISTORICAL_PHOTO_RECOVERY_2026-11-03',
    'MULTIFAMILY_OWNER_DISPLAY_RECOVERY_2026-11-03')
sub('MULTIFAMILY_HISTORICAL_RECOVERY',
    'MULTIFAMILY_OWNER_DISPLAY_RECOVERY')
exec(compile(s,str(source),"exec"),{
 "__name__":"__main__","__file__":str(source),
 "OWNER_HASHES":OWNER_HASHES,"RIGHTS_URL":RIGHTS_URL
})
