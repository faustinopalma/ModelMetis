"""Fetch files of a public Mendeley Data version and verify the publisher SHA-256 of each file."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://data.mendeley.com/public-api/datasets"
# Mendeley rejects urllib's default User-Agent with HTTP 403.
HEADERS = {"Accept": "application/json", "User-Agent": "ModelMetis-dataset-fetch/1.0"}


def get_json(url):
    with urlopen(Request(url, headers=HEADERS)) as response:
        return json.load(response)


def listing(dataset, version, prefix):
    folders = get_json(f"{API}/{dataset}/folders/{version}")
    by_id = {folder["id"]: folder for folder in folders}
    entries = []
    for folder in folders:
        parent = by_id.get(folder.get("parent_id"))
        if parent is None or (prefix and not parent["name"].startswith(prefix)):
            continue
        relative = Path(parent["name"]) / folder["name"]
        for item in get_json(f"{API}/{dataset}/files?folder_id={folder['id']}&version={version}"):
            details = item["content_details"]
            entries.append({"path": str(relative / item["filename"]), "size": item["size"],
                            "sha256": details["sha256_hash"], "url": details["download_url"]})
    if not entries:
        raise ValueError("No files matched the requested dataset version and folder prefix.")
    return sorted(entries, key=lambda entry: entry["path"])


def fetch(entry, root):
    target = root / entry["path"]
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
        return "present"
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(entry["url"], headers={"User-Agent": HEADERS["User-Agent"]})) as response:
        payload = response.read()
    if len(payload) != entry["size"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ValueError(f"Publisher size or SHA-256 mismatch: {entry['path']}")
    target.write_bytes(payload)
    return "downloaded"


def run(dataset, version, prefix, output):
    root = Path(output).resolve()
    entries = listing(dataset, version, prefix)
    states = [fetch(entry, root) for entry in entries]
    manifest = {"dataset": dataset, "version": version, "folder_prefix": prefix,
                "files": entries, "downloaded": states.count("downloaded"),
                "already_present": states.count("present")}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return {key: manifest[key] for key in ("dataset", "version", "downloaded", "already_present")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--prefix", default="", help="Keep top-level folders with this prefix.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.dataset, args.version, args.prefix, args.output)))
