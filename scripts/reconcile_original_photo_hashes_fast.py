#!/usr/bin/env python3
"""Fast, metadata-only Hays Botany original-photo reconciliation.

Uses GitHub tree objects and transferred source manifests, not clones or
individual media downloads. Reconciles the seven grouped-family archives.
Does NOT approve licenses, publish media or alter original source records.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

OWNER = "Crking92"
FAMILIES = (
    "Trees-Shrubs", "Lamiales", "Monocots-Aquatics", "Mixed-Families",
    "Spurges-Mallows", "Asterid-Allies", "Cacti-Buttercups",
)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "HaysBotanyOriginalPhotoHashReconciliation/1.0",
}
if os.getenv("GH_TOKEN"):
    HEADERS["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]


def github_json(endpoint):
    url = "https://api.github.com/repos/" + OWNER + "/" + endpoint
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError("GitHub API failed for " + url + ": " + str(exc)) from exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def github_file(repo, path, ref):
    uri = repo + "/contents/" + urllib.parse.quote(path) + "?ref=" + urllib.parse.quote(ref, safe="")
    result = github_json(uri)
    if result.get("type") != "file" or result.get("encoding") != "base64":
        raise ValueError("Expected inline manifest bytes for " + repo + "/" + path)
    return json.loads(base64.b64decode(result["content"]).decode("utf-8")), result["sha"]


def match_status(manifest_row, media_by_sha):
    sha = manifest_row["git_blob_sha"]
    paths = media_by_sha.get(sha, ())
    if not paths:
        return "NOT_EXACTLY_PUBLISHED"
    parts = Path(manifest_row["source_path"]).parts
    # An archived photo can have images/images/<name>; take the component
    # before the FIRST images folder, not a fixed offset from the filename.
    species = parts[parts.index("images")-1] if "images" in parts and parts.index("images") >= 1 else (parts[-3] if len(parts) >= 7 else "")
    if parts[-2] == "genus-images":
        stem = Path(manifest_row["source_path"]).stem
        if any(Path(path).parent.name in stem for path in paths):
            return "EXACT_GENUS_IMAGE_IN_NAMED_SPECIES_MEDIA"
        return "EXACT_OTHER_SITE_MEDIA_REVIEW"
    if species and any(path.startswith("site/media/" + species + "/") for path in paths):
        return "EXACT_IN_SPECIES_MEDIA"
    return "EXACT_OTHER_SITE_MEDIA_REVIEW"


def audit_family(family):
    repo = "Hays-Botany-" + family
    tree = github_json(repo + "/git/trees/main?recursive=1")
    if tree.get("truncated"):
        raise ValueError("Refusing incomplete GitHub tree: " + repo)
    media_by_sha = {}
    for entry in tree["tree"]:
        if entry.get("type") == "blob" and entry["path"].startswith("site/media/"):
            media_by_sha.setdefault(entry["sha"], []).append(entry["path"])
    transfer, transfer_sha = github_file(
        repo, "migration/original-source-transfer-manifest.json",
        "staging/original-source-transfer")
    history, history_sha = github_file(
        repo, "workflow/multi-family-historical-recovery-2026-11-03.json", "main")
    archive = [r for r in transfer["files"] if r.get("class") == "PRIVATE_MEDIA_HOLD"]
    historical = {}
    for batch in [*history.get("previous_batches", []), history]:
        for row in batch.get("records", []):
            if row.get("git_blob_sha"):
                historical[row["git_blob_sha"]] = row
    owner_closed = {
        row["git_blob_sha"] for row in
        history.get("owner_20261103_hold_closures", {}).get("records", [])
        if row.get("git_blob_sha")
    }
    stats = Counter()
    absent = []
    for row in archive:
        status = match_status(row, media_by_sha)
        stats[status] += 1
        if status.startswith("EXACT_"):
            continue
        previous = historical.get(row["git_blob_sha"], {})
        previous_status = previous.get("status", "NOT_IN_214_HISTORICAL_HOLD_REVIEW")
        stats["UNMATCHED_" + previous_status] += 1
        if row["git_blob_sha"] in owner_closed:
            stats["OWNER_CLOSED_EXCLUDED_UNMATCHED"] += 1
        absent.append({
            "repository": repo,
            "source_path": row["source_path"],
            "archive_path": row["destination"],
            "source_blob_sha": row["git_blob_sha"],
            "bytes": row.get("bytes"),
            "historical_review_status": previous_status,
            "historical_review_reason": previous.get("reason"),
            "owner_closed_excluded": row["git_blob_sha"] in owner_closed,
        })
    return {
        "repository": OWNER + "/" + repo,
        "main_tree_sha": tree["sha"],
        "source_manifest_blob_sha": transfer_sha,
        "historical_review_blob_sha": history_sha,
        "original_archive_photos": len(archive),
        "site_media_files": sum(map(len, media_by_sha.values())),
        "counts": dict(stats),
        "unmatched_photos": absent,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/exports/original_photo_reconciliation_current.json")
    args = parser.parse_args()
    audits = []
    combined = Counter()
    for family in FAMILIES:
        record = audit_family(family)
        audits.append(record)
        combined.update(record["counts"])
        print("HAYS_FAST_ARCHIVE_RECONCILED", json.dumps({
            "repository": record["repository"],
            "original_archive_photos": record["original_archive_photos"],
            "exact_in_species_media": record["counts"].get("EXACT_IN_SPECIES_MEDIA", 0),
            "exact_elsewhere": record["counts"].get("EXACT_OTHER_SITE_MEDIA_REVIEW", 0),
            "no_exact": record["counts"].get("NOT_EXACTLY_PUBLISHED", 0),
        }), flush=True)
    report = {
        "schema_version": 1,
        "description": "Metadata-only cross-family original-photo inventory. Not a license approval, taxon verification or live Pages test.",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "family_count": len(audits),
        "original_archive_photos": sum(x["original_archive_photos"] for x in audits),
        "counts": dict(combined),
        "family_audits": audits,
        "important": [
            "The original 481-record subgroup is NOT equivalent to all unmatched archives.",
            "Historical HELD status represents prior audit classification, not necessarily today's final rights disposition.",
            "Exact GitHub site/media file does not itself prove the photo is referenced and visible on public Pages.",
            "Never automatically publish nonexact archival photos without checking source rights and basic species plausibility.",
        ],
    }
    assert report["original_archive_photos"] == (
        combined["EXACT_IN_SPECIES_MEDIA"] +
        combined["EXACT_GENUS_IMAGE_IN_NAMED_SPECIES_MEDIA"] +
        combined["EXACT_OTHER_SITE_MEDIA_REVIEW"] +
        combined["NOT_EXACTLY_PUBLISHED"]
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("HAYS_FAST_BULK_RECONCILIATION_SUMMARY", json.dumps({
        "original_archive_photos": report["original_archive_photos"],
        **dict(combined),
        "output": str(out),
    }), flush=True)


if __name__ == "__main__":
    main()
