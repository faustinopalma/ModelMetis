import argparse
import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path

from modelmetis.dsp_packet import read_bound
from modelmetis.dsp_report import STYLE, THEME
from modelmetis.visual_audio import canonical_json

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).parent / "templates/audio_comparison.html"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def data_url(payload, media):
    return f"data:{media};base64," + base64.b64encode(payload).decode()


def pack_record(folder, item):
    source = Path(item["wav"])
    audio = source.read_bytes()
    if sha256(audio) != item["audio_sha256"]:
        raise ValueError("Listening input differs from its registered WAV.")
    report = folder / "reports" / item["id"]
    manifest = read_json(report / "manifest.json")
    if manifest["status"] != "completed":
        raise ValueError("Comparison requires a completed DSP report.")
    evidence = json.loads(read_bound(report, "evidence.json", manifest))
    provenance = json.loads(read_bound(report, "provenance.json", manifest))
    if provenance["source_sha256"] != item["audio_sha256"]:
        raise ValueError("Audio and displayed DSP report belong to different sources.")
    if len(evidence["channels"]) != 1 or len(evidence["channels"][0]["segments"]) != 1:
        raise ValueError("This listening view requires one complete mono analysis interval.")
    figures, hashes = {}, {}
    for image in evidence["channels"][0]["segments"][0]["images"]:
        payload = read_bound(report, image["path"], manifest)
        if sha256(payload) != image["sha256"]:
            raise ValueError("Displayed figure differs from DSP evidence.")
        key = Path(image["path"]).stem.rsplit("-", 1)[-1]
        figures[key] = data_url(payload, "image/png")
        hashes[key] = sha256(payload)
    return {
        "id": item["id"],
        "audio": data_url(audio, "audio/wav"),
        "figures": figures,
        "duration": evidence["duration_seconds"],
        "rate": evidence["sample_rate"],
        "audioHash": item["audio_sha256"],
        "figureHashes": hashes,
    }


def load_dataset(folder, name):
    folder = Path(folder)
    registration = read_json(folder / "registration.json")
    protocol_bytes = (folder / "protocol.json").read_bytes()
    truth_bytes = (folder / "sealed/truth.json").read_bytes()
    if (
        sha256(protocol_bytes) != registration["protocol_sha256"]
        or sha256(truth_bytes) != registration["truth_sha256"]
    ):
        raise ValueError("Experiment registration changed.")
    protocol, truth = json.loads(protocol_bytes), json.loads(truth_bytes)
    references = [
        pack_record(folder, item)
        | {
            "condition": item["condition_id"],
            "label": item["label"],
        }
        for item in protocol["known"]
    ]
    queries = []
    for item in protocol["queries"]:
        attempts = sorted(folder.glob(f"round-*/*/{item['id']}/03_response/attempt.json"))
        if not attempts:
            continue
        models = []
        for path in attempts:
            if path.parents[2].name not in {"development", "final", "replay-known"}:
                continue
            receipt = read_json(path)
            decision = receipt.get("decision")
            models.append(
                {
                    "round": path.parents[3].name,
                    "phase": path.parents[2].name,
                    "status": receipt["status"],
                    "condition": decision.get("condition_id") if decision else None,
                    "outcome": decision.get("outcome") if decision else None,
                }
            )
        queries.append(
            pack_record(folder, item)
            | {
                "group": item["role"],
                "truth": truth[item["id"]]["condition_id"],
                "models": models,
            }
        )
    queries.sort(key=lambda item: sha256(("human-comparison-v1:" + item["audioHash"]).encode()))
    if not queries or not references:
        raise ValueError("A comparison dataset must contain references and evaluated queries.")
    return {
        "name": name,
        "key": folder.name,
        "protocolHash": sha256(protocol_bytes),
        "references": references,
        "queries": queries,
    }


def load_icons():
    program = """
const React = require('./apps/console/node_modules/react');
const {renderToStaticMarkup} = require('./apps/console/node_modules/react-dom/server');
const lucide = require('./apps/console/node_modules/lucide-react');
const names = ['ChevronLeft','ChevronRight','Play','Pause','RotateCcw','Repeat2',
  'Download','Eye','Check','Maximize2','X','Headphones','ArrowLeftRight'];
console.log(JSON.stringify(Object.fromEntries(names.map(name => [name,
  renderToStaticMarkup(React.createElement(lucide[name], {size:20, 'aria-hidden':true}))]))));
"""
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def build(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new output folder to preserve listening sessions.")
    datasets = [
        load_dataset(ROOT / "outputs/dsp-jin-v1", "Jin"),
        load_dataset(ROOT / "outputs/dsp-ottawa-v2", "Ottawa"),
    ]
    payload = {"schema": 1, "datasets": datasets, "icons": load_icons()}
    fingerprint = sha256(
        canonical_json(
            [{"key": item["key"], "protocolHash": item["protocolHash"]} for item in datasets]
        )
    )
    payload["fingerprint"] = fingerprint
    encoded = canonical_json(payload).decode().replace("<", "\\u003c")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__THEME__", THEME).replace("__BASE_STYLE__", STYLE)
    page = page.replace("__DATA__", encoded)
    output.mkdir(parents=True)
    (output / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "schema": 1,
        "fingerprint": fingerprint,
        "page_sha256": sha256(page.encode()),
        "generator_sha256": sha256(Path(__file__).read_bytes()),
        "template_sha256": sha256(TEMPLATE.read_bytes()),
        "datasets": [
            {
                "name": item["name"],
                "protocol_sha256": item["protocolHash"],
                "references": len(item["references"]),
                "queries": len(item["queries"]),
                "audio_sha256": [
                    record["audioHash"] for record in [*item["references"], *item["queries"]]
                ],
            }
            for item in datasets
        ],
        "mode": "reference-review",
        "labels": "Publisher labels always visible; matching reference selected for each query",
    }
    (output / "manifest.json").write_bytes(canonical_json(manifest))
    return {
        "output": str(output),
        "html_bytes": len(page.encode()),
        "datasets": [
            {key: item[key] for key in ("name", "references", "queries")}
            for item in manifest["datasets"]
        ],
    }


if __name__ == "__main__":
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Offline human audio and DSP comparison page.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output), indent=2))
    finally:
        print(f"ElapsedSeconds={time.perf_counter() - started:.3f}", flush=True)
