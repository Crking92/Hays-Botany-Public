#!/usr/bin/env python3
"""Read-only audit of ALL current family Pages galleries.

Compare immutable main-branch snapshots to live Pages JSON and species cards,
then HEAD every locally hosted image referenced by the live cards. This does
not approve, publish, delete, redownload, or modify botanical source records.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

REPOSITORIES = (
    "Hays-Botany-Asteraceae",
    "Hays-Botany-Fabaceae",
    "Hays-Botany-Poaceae",
    "Hays-Botany-Monocots-Aquatics",
    "Hays-Botany-Lamiales",
    "Hays-Botany-Asterid-Allies",
    "Hays-Botany-Cacti-Buttercups",
    "Hays-Botany-Spurges-Mallows",
    "Hays-Botany-Trees-Shrubs",
    "Hays-Botany-Mixed-Families",
)
USER_AGENT = "HaysBotanyCurrentLiveGalleryAudit/2026-11-04"
TOKEN = os.environ.get("GH_TOKEN", "")
LIMIT = 12 * 1024 * 1024


def fetch(url: str, method: str = "GET", attempts: int = 2):
    last = None
    for attempt in range(attempts):
        try:
            headers = {"User-Agent": USER_AGENT, "Cache-Control": "no-cache"}
            if TOKEN and urllib.parse.urlsplit(url).hostname == "api.github.com":
                headers["Authorization"] = "Bearer " + TOKEN
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=22) as response:
                if response.status != 200:
                    raise ValueError("HTTP " + str(response.status))
                if method == "HEAD":
                    return dict(response.headers)
                payload = response.read(LIMIT + 1)
                if len(payload) > LIMIT:
                    raise ValueError("Metadata exceeds safe size")
                return payload
        except Exception as exc:
            last = str(exc)
            if attempt + 1 < attempts:
                time.sleep(attempt + 1)
    raise RuntimeError(last)


def head_source(repo):
    info = json.loads(fetch("https://api.github.com/repos/Crking92/" + repo + "/branches/main"))
    return info["commit"]["sha"]


def source_url(repo, sha, path):
    return "https://raw.githubusercontent.com/Crking92/" + repo + "/" + sha + "/" + path


def site_url(repo):
    return "https://crking92.github.io/" + repo + "/site/"


def metadata(repo):
    item = {"repository": repo, "status": "CHECKING", "species": 0,
            "gallery_placements": 0, "photo_species": 0, "photos_checked": 0,
            "errors": []}
    try:
        sha = head_source(repo)
        item["main_sha"] = sha
        root = site_url(repo)
        grass = repo == "Hays-Botany-Poaceae"
        index_path = "site/data/poaceae-index.json" if grass else "site/data/collection-index.json"
        for path in ("site/data/gallery-index.json", index_path):
            expected = fetch(source_url(repo, sha, path))
            live = fetch(root + path.removeprefix("site/") + "?sha=" + sha[:12])
            if hashlib.sha256(expected).digest() != hashlib.sha256(live).digest():
                item["status"] = "DEPLOYMENT_BEHIND_MAIN"
                item["errors"].append("Live Pages bytes differ from main: " + path)
                return item, []
            if path.endswith("gallery-index.json"):
                gallery = json.loads(live)
            else:
                rows = json.loads(live)
        if not grass:
            rows = rows["entries"]
        expected_species = gallery["species"]
        expected_photo_count = gallery["photo_panels"] if grass else gallery["photo_count"]
        expected_with_photos = gallery["photo_species"]
        if len(rows) != expected_species or len(gallery["entries"]) != expected_species:
            raise ValueError("Species index/gallery species totals differ")
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError("Duplicate species IDs in live collection index")
        counts = [row["local_panel_count"] if grass else row["photo_count"] for row in rows]
        if sum(counts) != expected_photo_count:
            raise ValueError("Gallery photo count differs from species index sum")
        if sum(n > 0 for n in counts) != expected_with_photos:
            raise ValueError("Photo species count differs from gallery index")
        for row, n in zip(rows, counts):
            if gallery["entries"][row["id"]]["count"] != n:
                raise ValueError("Gallery count differs on species " + row["id"])
        item.update(species=expected_species, gallery_placements=expected_photo_count,
                    photo_species=expected_with_photos, status="INDEX_CURRENT")
        return item, [(repo, sha, row["id"], n, grass) for row, n in zip(rows, counts)]
    except Exception as exc:
        item["status"] = "ERROR"
        item["errors"].append(str(exc)[:260])
        return item, []


def inspect_card(task):
    repo, sha, sid, expected_count, grass = task
    path = "site/data/species/" + sid + ".json"
    root = site_url(repo)
    try:
        upstream = fetch(source_url(repo, sha, path))
        live = fetch(root + path.removeprefix("site/") + "?sha=" + sha[:12])
        if upstream != live:
            raise ValueError("Published card differs from current main")
        card = json.loads(live)
        if card["id"] != sid:
            raise ValueError("Card ID mismatch")
        photographs = card.get("panels") if grass else card.get("verified_photos")
        if not isinstance(photographs, list) or len(photographs) != expected_count:
            raise ValueError("Card count differs from current gallery")
        image_urls = []
        for photo in photographs:
            for key in ("src", "creator", "license", "source_page"):
                if not isinstance(photo.get(key), str) or not photo[key].strip():
                    raise ValueError("Photo missing " + key)
            image_url = urllib.parse.urljoin(root, photo["src"])
            if not image_url.startswith("https://crking92.github.io/" + repo + "/"):
                raise ValueError("Photo not hosted within its family Pages site: " + photo["src"])
            if photo.get("private_rights_review_only") is True:
                raise ValueError("Rights-held photo appears in public gallery")
            image_urls.append(image_url)
        return repo, sid, image_urls, None
    except Exception as exc:
        return repo, sid, [], str(exc)[:250]


def check_live_image(url):
    try:
        headers = fetch(url, "HEAD")
        mime = headers.get("Content-Type", "").lower()
        if not (mime.startswith("image/") or mime.startswith("application/octet-stream")):
            raise ValueError("Not an image media type: " + mime)
        if headers.get("Content-Length") and int(headers["Content-Length"]) < 100:
            raise ValueError("Image response is unexpectedly small")
        return url, None
    except Exception as exc:
        return url, str(exc)[:230]


def check_one_pixel_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=25) as response:
            img = response.read(25 * 1024 * 1024 + 1)
        if len(img) > 25 * 1024 * 1024:
            raise ValueError("Sample photo exceeds 25 MB")
        with Image.open(io.BytesIO(img)) as picture:
            picture.verify()
        return url, None
    except Exception as exc:
        return url, str(exc)[:200]


def main():
    results = []
    tasks = []
    for repo in REPOSITORIES:
        record, card_tasks = metadata(repo)
        results.append(record)
        tasks.extend(card_tasks)
        print("FAMILY_LIVE_METADATA", json.dumps({k: v for k, v in record.items()
              if k != "errors"}), flush=True)

    by_name = {x["repository"]: x for x in results}
    photo_urls = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as workers:
        for repo, sid, urls, error in workers.map(inspect_card, tasks):
            record = by_name[repo]
            if error:
                record["errors"].append(sid + ": " + error)
            else:
                for url in urls:
                    photo_urls.setdefault(url, set()).add(repo)
    for record in results:
        if record["status"] == "INDEX_CURRENT":
            if record["errors"]:
                record["status"] = "CARD_MISMATCH"
            else:
                record["status"] = "CARDS_CURRENT"

    # HEAD every DISTINCT photo, including grass comparison panels. This
    # checks all browser-visible URLs without redownloading thousands of MB.
    urls = sorted(photo_urls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as workers:
        for url, error in workers.map(check_live_image, urls):
            for repo in photo_urls[url]:
                record = by_name[repo]
                record["photos_checked"] += 1
                if error and len(record["errors"]) < 35:
                    record["errors"].append(url + ": " + error)

    # Decode one real image per family; URL existence alone cannot test pixels.
    samples = []
    for repo in REPOSITORIES:
        choices = [url for url in urls if repo in photo_urls[url]]
        if choices:
            samples.append((repo, choices[0]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as workers:
        sample_results = list(workers.map(check_one_pixel_image, [url for _, url in samples]))
    for (repo, _), (_, error) in zip(samples, sample_results):
        if error:
            by_name[repo]["errors"].append("Sample pixel decode: " + error)
        else:
            by_name[repo]["sample_image_decoded"] = True

    for record in results:
        if record["status"] == "CARDS_CURRENT":
            if record["errors"]:
                record["status"] = "IMAGE_OR_CARD_ERROR"
            else:
                record["status"] = "LIVE_VERIFIED"
        print("FAMILY_LIVE_PHOTOS", json.dumps(record, sort_keys=True), flush=True)

    summary = {
        "audit": "HAYS_BOTANY_CURRENT_LIVE_PHOTO_GALLERIES",
        "families_tested": len(results),
        "families_verified": sum(x["status"] == "LIVE_VERIFIED" for x in results),
        "published_gallery_placements": sum(x["gallery_placements"] for x in results),
        "distinct_image_urls_tested": len(urls),
        "status": "PASS" if all(x["status"] == "LIVE_VERIFIED" for x in results) else "NEEDS_ATTENTION",
        "results": results,
        "writes_to_family_repositories": 0,
    }
    Path("qa-report").mkdir(exist_ok=True)
    Path("qa-report/live-photo-galleries.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("HAYS_BOTANY_CURRENT_LIVE_AUDIT", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
