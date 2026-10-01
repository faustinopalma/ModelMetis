import argparse
import base64
import copy
import hashlib
import html
import json
from html.parser import HTMLParser
from pathlib import Path

from modelmetis.dsp_report import STYLE, THEME, digest
from modelmetis.dsp_similarity import validate_result
from modelmetis.visual_audio import canonical_json
from scripts.audio_comparison import ROOT
from scripts.dsp_extended_experiment import read_json, write_json

DATASETS = {
    "Jin": {
        "authors": "Linjie Jin",
        "source": "https://data.mendeley.com/datasets/9dpmkgpncw/1",
        "doi": "10.17632/9dpmkgpncw.1",
        "changes": "Ten-second mono PCM16 excerpts; DC removal and peak normalization.",
    },
    "Ottawa": {
        "authors": "Mert Sehri and Patrick Dumond",
        "source": "https://data.mendeley.com/datasets/msxs4vj48g/2",
        "doi": "10.17632/msxs4vj48g.2",
        "changes": "Microphone column exported as ten-second mono PCM16; peak normalized.",
    },
}
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


class PayloadParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.chunks = []
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "comparison-data":
            self.active = True
            self.count += 1

    def handle_data(self, data):
        if self.active:
            self.chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

    def extract(self, page):
        self.feed(page)
        if self.count != 1 or not self.chunks:
            raise ValueError("Expected exactly one nonempty review payload.")
        encoded = "".join(self.chunks)
        return encoded, json.loads(encoded)


def publish_asset(url, expected_hash, media_type, output):
    prefix = f"data:{media_type};base64,"
    if not url.startswith(prefix):
        raise ValueError("Only bound embedded WAV/PNG assets can be published.")
    payload = base64.b64decode(url[len(prefix):], validate=True)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_hash:
        raise ValueError("Published media differs from its recorded hash.")
    suffix = "wav" if media_type == "audio/wav" else "png"
    relative = f"media/{actual}.{suffix}"
    path = Path(output) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if digest(path) != actual:
            raise ValueError("Existing deduplicated media changed.")
    else:
        path.write_bytes(payload)
    return relative


def public_payload(payload, output):
    result = copy.deepcopy(payload)
    records = []
    for dataset in result["datasets"]:
        if dataset["name"] not in DATASETS:
            raise ValueError("Dataset publication rights are not documented.")
        for record in [*dataset["references"], *dataset["queries"]]:
            record["audio"] = publish_asset(
                record["audio"], record["audioHash"], "audio/wav", output
            )
            for view, url in record["figures"].items():
                record["figures"][view] = publish_asset(
                    url, record["figureHashes"][view], "image/png", output
                )
            records.append({
                "dataset": dataset["name"], "record_id": record["id"],
                "class": record.get("truth", record.get("condition")),
                "audio": record["audio"], "audio_sha256": record["audioHash"],
                "figures": record["figures"], "figure_sha256": record["figureHashes"],
                "sample_rate": record["rate"], "duration_seconds": record["duration"],
            })
    result["pageTitle"] = "ModelMetis / Archived pruning candidate"
    return result, records


def export_decision(case, source, output):
    path = (Path(source) / html.unescape(case["responseLink"])).resolve()
    if not path.is_relative_to(ROOT / "outputs") or path.name != "response.json":
        raise ValueError("Unexpected evidence location.")
    receipt = read_json(path.parent / "attempt.json")
    registration_path = path.parent.parent / "registration.json"
    registration = read_json(registration_path)
    entries = [entry for entry in registration["cases"] if entry["name"] == case["id"]]
    if len(entries) != 1:
        raise ValueError("Unregistered published decision.")
    entry = entries[0]
    for filename, field in (
        ("request.json", "request_sha256"), ("contract.json", "contract_sha256")
    ):
        if digest(path.parent / filename) != entry[field]:
            raise ValueError("Published decision input changed.")
    if (receipt["status"] != "completed" or digest(path) != receipt["response_sha256"]
            or receipt["request_sha256"] != entry["request_sha256"]):
        raise ValueError("Published response binding failed.")
    decision = json.loads(read_json(path)["choices"][0]["message"]["content"])
    contract = read_json(path.parent / "contract.json")
    validate_result(decision, contract["known_evidence"], contract["unknown_evidence"])
    if decision != receipt["decision"] or decision["explanation"] != case["explanation"]:
        raise ValueError("Visible answer differs from the recorded response.")
    relative = f"responses/{case['id']}.json"
    destination = Path(output) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, {
        "decision": decision, "model": receipt["returned_model"],
        "source_request_sha256": receipt["request_sha256"],
        "source_response_sha256": receipt["response_sha256"],
        "publication": "Exact parsed decision; transport identifiers and cloud metadata omitted.",
    })
    request = read_json(path.parent / "request.json")
    public_messages = []
    images = []
    for message in request["messages"]:
        if isinstance(message["content"], str):
            public_messages.append(message)
            continue
        parts = []
        for part in message["content"]:
            if part["type"] == "text":
                parts.append(part)
            else:
                image = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
                images.append({"sha256": hashlib.sha256(image).hexdigest(),
                               "detail": part["image_url"]["detail"]})
        public_messages.append({"role": message["role"], "content": parts})
    inputs = Path(output) / "inputs"
    inputs.mkdir(exist_ok=True)
    write_json(inputs / f"{case['id']}.json", {
        "messages": public_messages, "response_format": request["response_format"],
        "reasoning_effort": request["reasoning_effort"],
        "max_completion_tokens": request["max_completion_tokens"],
        "contact_sheets": images, "source_request_sha256": receipt["request_sha256"],
        "publication": "Exact text parts and schema; embedded model contact sheets omitted. "
        "The media directory provides full-resolution plots for the four displayed views.",
    })
    case["responseLink"] = relative


def export_comparisons(output, refresh=False):
    directory = Path(output) / "results"
    directory.mkdir(parents=True, exist_ok=refresh)
    pruning = ROOT / "outputs/dsp-pruning-cross-v1"
    from scripts.dsp_extended_review import validated_decisions

    decisions = validated_decisions(pruning)
    rows = [{key: row[key] for key in (
        "name", "source_case", "block", "arm", "removed", "dataset", "phase", "query_id",
        "expected", "predicted", "category", "request_sha256")}
        | {"response_sha256": row["receipt"]["response_sha256"]} for row in decisions]
    if len(rows) != 46:
        raise ValueError("Expected all 46 final crossed-study outcomes.")
    write_json(directory / "pruning-decisions.json", rows)
    write_json(directory / "pruning-summary.json", read_json(pruning / "crossed-results.json"))
    write_json(directory / "pruning-input-audit.json", read_json(pruning / "input-audit.json"))
    registration = read_json(pruning / "registration.json")
    write_json(directory / "pruning-registration.json", {
        **{key: registration[key] for key in (
            "cases", "factor_order", "cases_by_block", "protocol_sha256", "code_sha256",
            "source_registration_sha256", "settings_sha256", "truth_sha256", "stop_rule")},
        "publication": "Registration extract; authorization and spending metadata omitted.",
        "original_sha256": digest(pruning / "registration.json"),
    })
    family = ROOT / "outputs/dsp-family-separation-v1"
    manifest = read_json(family / "manifest.json")
    names = ["summary.json", "jin-summary.png", "jin-families.png",
             "ottawa-summary.png", "ottawa-families.png"]
    for name in names:
        if digest(family / name) != manifest["files"][name]:
            raise ValueError("Selected family evidence changed.")
        destination = "family-separation.json" if name == "summary.json" else name
        (directory / destination).write_bytes((family / name).read_bytes())
    write_json(directory / "family-registration.json", read_json(family / "registration.json"))
    audit = ROOT / "outputs/dsp-diagram-audit-v4"
    write_json(directory / "diagram-audit.json", read_json(audit / "evaluation.json"))
    audit_registration = read_json(audit / "registration.json")
    write_json(directory / "diagram-audit-registration.json", {
        **{key: audit_registration[key] for key in (
            "jobs", "baseline", "selection", "limitations", "truth_sha256", "code_sha256")},
        "publication": "Registration extract; local continuation paths "
        "and account settings omitted.",
        "original_sha256": digest(audit / "registration.json"),
    })
    write_json(directory / "provenance.json", {
        "pruning_registration_sha256": digest(pruning / "registration.json"),
        "family_manifest_sha256": digest(family / "manifest.json"),
        "scope": "Selected completed development evidence, not new inference or final testing.",
    })


def seal(output):
    output = Path(output)
    write_json(output / "manifest.json", {"files": {
        path.relative_to(output).as_posix(): digest(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path != output / "manifest.json"
    }})


def publish(source, output, refresh=False):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Never overwrite the frozen local source snapshot.")
    manifest = read_json(source / "manifest.json")
    if digest(source / "index.html") != manifest["files"]["index.html"]:
        raise ValueError("Source comparison changed.")
    page = (source / "index.html").read_text(encoding="utf-8")
    encoded, payload = PayloadParser().extract(page)
    output.mkdir(parents=True, exist_ok=refresh)
    public, records = public_payload(payload, output)
    for case in public["cases"]:
        export_decision(case, source, output)
    page = page.replace(encoded, canonical_json(public).decode().replace("<", "\\u003c"), 1)
    page = page.replace('>Raw response</a>', '>Published decision</a>')
    page = page.replace(
        '<div class="header-actions"></div>',
        '<div class="header-actions"><a href="../index.html">Archive</a>'
        '<a href="../../index.html">Current method</a>'
        '<a href="https://github.com/faustinopalma/ModelMetis/blob/main/examples/'
        'archive/pruning-candidate/README.md">Sources and scope</a></div>',
    )
    page = page.replace(
        '<span id="attribution"></span>',
        '<span id="attribution"></span> / <a href="https://github.com/faustinopalma/'
        'ModelMetis/blob/main/examples/archive/pruning-candidate/ATTRIBUTION.md">Attribution</a>',
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    write_json(output / "provenance.json", {
        "datasets": {name: {**metadata, "license": LICENSE_URL}
                     for name, metadata in DATASETS.items()},
        "records": records, "source_manifest_sha256": digest(source / "manifest.json"),
        "source_experiment_sha256": manifest["experiment_sha256"],
        "display_views": manifest["display_views"],
        "model_view_count": manifest["model_view_count"],
        "policy_adopted": False, "primary_decisions": 8, "repeats": 2,
    })
    seal(output)
    print(f"Public comparison: {output / 'index.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish the archived, hash-bound pruning review.")
    parser.add_argument("--source", type=Path, default=Path("outputs/audio-comparison-v15"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results", action="store_true")
    parser.add_argument("--results-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if not args.results_only:
        publish(args.source, args.output, refresh=args.refresh)
    if args.results or args.results_only:
        export_comparisons(args.output.parent, refresh=args.results_only or args.refresh)
        template = ROOT / "scripts/templates/evidence_index.html"
        page = template.read_text(encoding="utf-8")
        (args.output.parent / "index.html").write_text(
            page.replace("__THEME__", THEME).replace("__BASE_STYLE__", STYLE), encoding="utf-8"
        )
        seal(args.output.parent)