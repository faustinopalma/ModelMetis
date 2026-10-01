import argparse
import base64
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

from modelmetis.dsp_guide import VIEW_GUIDE
from modelmetis.dsp_packet import read_bound
from modelmetis.dsp_report import STYLE, THEME, digest
from modelmetis.dsp_similarity import validate_result
from modelmetis.visual_audio import canonical_json
from scripts.dsp_extended_review import simple_review_data
from scripts.publish_evidence import DATASETS, LICENSE_URL, seal

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = Path(__file__).parent / "templates"
VIEWS = ("levels", "fft", "welch", "stft", "bands", "envelope", "autocorrelation", "overview")
OVERVIEW = ("Complete recording", "Time (s), min/max waveform envelope and RMS/peak per 20 ms "
            "frame for the whole ten-second excerpt. It shares the waveform view's level scale.")
METHODS = {
    "A": "Reports only",
    "B": "Reports plus Welch spectral distances",
    "C": "Calibrated distance rule (exploratory replay)",
}
ROUNDS = {
    ("dsp-ottawa-v1", "round-01"): "A", ("dsp-ottawa-v1", "round-02"): "A",
    ("dsp-ottawa-v1", "round-03"): "A", ("dsp-ottawa-v2", "round-01"): "A",
    ("dsp-ottawa-v2", "round-02"): "A", ("dsp-jin-v1", "round-01"): "A",
    ("dsp-jin-v1", "round-02"): "B", ("dsp-jin-v1", "round-03"): "C",
}
PHASES = {"development": "development", "final": "reserved", "novelty": "excluded",
          "replay-known": "reserved", "replay-novelty": "excluded"}
COLLECTIONS = (
    {"key": "jin-distances", "dataset": "Jin", "folder": "dsp-jin-v1", "round": "round-02",
     "name": "Jin: reports + distances", "phases": ("final", "novelty"),
     "expected": {"Correct class": 11, "False rejection": 1, "Correct rejection": 2,
                  "Wrong acceptance": 2}},
    {"key": "ottawa-reports", "dataset": "Ottawa", "folder": "dsp-ottawa-v2",
     "round": "round-02", "name": "Ottawa: reports only", "phases": ("development",),
     "expected": {"Correct class": 4, "Wrong class": 12}},
    {"key": "jin-calibrated", "dataset": "Jin", "folder": "dsp-jin-v1", "round": "round-03",
     "name": "Jin: calibrated replay", "phases": ("replay-known", "replay-novelty"),
     "expected": {"Correct class": 9, "False rejection": 3, "Correct rejection": 4}},
)
EXAMPLES = (
    ("jin-distances-reserved-T01", "Correct class", "Recognition",
     "An unseen right-microphone window of excess Hall adhesive matches its front-microphone "
     "reference at 3.15 dB; every other reference is at least 7.6 dB away."),
    ("jin-distances-excluded-T01", "Correct rejection", "Abstention",
     "The same window, with its own reference withheld. The nearest remaining reference is "
     "7.6 dB away and the model answers different."),
    ("jin-distances-reserved-T07", "False rejection", "Missed recognition",
     "Magnet fracture is 3.62 dB from its reference, farther than the 3.04 dB separating the "
     "magnet-fracture and tight-bearing references. The model abstains."),
    ("jin-distances-excluded-T04", "Wrong acceptance", "Unsafe acceptance",
     "A healthy window, with the healthy reference withheld, is 6.35 dB from tight bearing. "
     "The model notes the large distance, then accepts tight bearing anyway."),
    ("ottawa-reports-development-D01", "Correct class", "Recognition across operating profile",
     "A healthy profile-2 acquisition matches the healthy profile-1 reference."),
    ("ottawa-reports-development-D03", "Wrong class", "Wrong assignment across operating profile",
     "Rotor unbalance at profile 2 is assigned to stator winding; one reference per class "
     "does not represent the profile change."),
)
LIMITS = (
    "The recordings come from two public datasets already studied by the project; fresh "
    "recordings and blind listening comparisons are the next validation steps.",
    "Jin reserved windows come from four right-microphone acquisitions, three windows each.",
    "Ottawa uses eight motors; motor identity can be confounded with condition.",
    "Configuration C was designed after inspecting configuration B's reserved result.",
    "Configuration C thresholds use eight additional labeled left-microphone windows.",
    "Excluded-class tests withhold a known reference; genuinely new fault mechanisms are a "
    "separate future test.",
    "Forced nearest-reference distance alone labels all Jin reserved windows correctly; the "
    "next comparisons measure what the model adds beyond these numbers.",
)


PAGE_WORDING = (
    ('>Other / review errors<', '>Different / review errors<'),
    ("reason:'Other: the model selected no reference.'",
     "reason:'Different: the model selected no reference.'"),
    ("model.index<0?'Other':label", "model.index<0?'Different':label"),
    ("+' Other / review errors'", "+' different / review errors'"),
    ("item.expected==='different'?'Other':label", "item.expected==='different'?'different':label"),
    ("'Other / Human review needed'", "'Different / Human review needed'"),
    ("'Other (no reference selected)'", "'different (no reference selected)'"),
    ("expected response: Other.'", "expected response: different.'"),
    ("item.dataset==='Jin'?", "item.dataset.startsWith('Jin')?"),
    ('>Raw response</a>', '>Published decision</a>'),
    ('<footer>Recorded AI decisions / Original audio / Publisher labels / '
     'Human intervention not executed / ',
     '<footer>Recorded model decisions / Original audio / Publisher labels / '),
)


def reword(page):
    for old, new in PAGE_WORDING:
        if page.count(old) != 1:
            raise ValueError(f"Comparison template changed near {old!r}.")
        page = page.replace(old, new)
    return page


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def image_hash(url):
    return sha(base64.b64decode(url.split(",", 1)[1], validate=True))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(json.dumps(value, indent=2, ensure_ascii=False).encode() + b"\n")


def code_matches(path, recorded):
    content = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return recorded in {sha(content), sha(content.replace(b"\n", b"\r\n"))}


def store(payload, suffix, output):
    name = f"media/{sha(payload)}.{suffix}"
    target = Path(output) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) != sha(payload):
        raise ValueError("Existing content-addressed media changed.")
    if not target.exists():
        target.write_bytes(payload)
    return name


def registration(folder):
    record = read_json(folder / "registration.json")
    if (digest(folder / "protocol.json") != record["protocol_sha256"]
            or digest(folder / "sealed/truth.json") != record["truth_sha256"]):
        raise ValueError("Experiment registration changed.")
    return read_json(folder / "protocol.json"), read_json(folder / "sealed/truth.json")


def export_record(folder, item, output):
    report = folder / "reports" / item["id"]
    manifest = read_json(report / "manifest.json")
    if manifest["status"] != "completed":
        raise ValueError("Published records require completed DSP reports.")
    evidence = json.loads(read_bound(report, "evidence.json", manifest))
    provenance = json.loads(read_bound(report, "provenance.json", manifest))
    audio = Path(item["wav"]).read_bytes()
    if sha(audio) != item["audio_sha256"] or provenance["source_sha256"] != sha(audio):
        raise ValueError("Audio differs from its registered DSP source.")
    channel = evidence["channels"]
    if len(channel) != 1 or len(channel[0]["segments"]) != 1:
        raise ValueError("Expected one mono ten-second analysis interval.")
    images = [*channel[0]["segments"][0]["images"], channel[0]["overview_image"]]
    figures, hashes = {}, {}
    for image in images:
        payload = read_bound(report, image["path"], manifest)
        if sha(payload) != image["sha256"]:
            raise ValueError("Figure differs from its DSP evidence.")
        stem = Path(image["path"]).stem
        key = "overview" if stem.endswith("overview") else stem.rsplit("-", 1)[-1]
        figures[key], hashes[key] = store(payload, "png", output), image["sha256"]
    if set(figures) != set(VIEWS):
        raise ValueError("Every model-facing figure must be published.")
    return {"id": item["id"], "audio": store(audio, "wav", output), "audioHash": sha(audio),
            "figures": figures, "figureHashes": hashes, "rate": evidence["sample_rate"],
            "duration": evidence["duration_seconds"]}


def category(phase, expected, predicted):
    if phase == "excluded":
        return "Correct rejection" if predicted == "different" else "Wrong acceptance"
    if predicted == expected:
        return "Correct class"
    return "False rejection" if predicted == "different" else "Wrong class"


def load_case(folder, round_name, phase, query_id, truth, evaluation, labels):
    bundle = folder / round_name / phase / query_id
    manifest = read_json(bundle / "manifest.json")
    preparation = read_json(bundle / "preparation.json")
    if preparation["manifest_sha256"] != digest(bundle / "manifest.json"):
        raise ValueError("Bundle manifest changed.")
    for name, expected in manifest["bindings"].items():
        if name.startswith(("02_model/", "audit/")) and digest(bundle / name) != expected:
            raise ValueError("Bound model input changed.")
    rows = [row for row in evaluation["rows"] if row["id"] == query_id]
    receipt = read_json(bundle / "03_response/attempt.json")
    if (len(rows) != 1 or rows[0]["receipt_sha256"] != digest(bundle / "03_response/attempt.json")
            or rows[0]["request_sha256"] != manifest["request_sha256"]
            or receipt["request_sha256"] != digest(bundle / "02_model/request.json")
            or receipt["status"] != "completed"
            or receipt["response_sha256"] != digest(bundle / "03_response/response.json")):
        raise ValueError("Recorded request, receipt or response binding failed.")
    response = read_json(bundle / "03_response/response.json")
    decision = json.loads(response["choices"][0]["message"]["content"])
    if decision != receipt["decision"]:
        raise ValueError("Receipt decision differs from the actual response.")
    validate_result(decision, manifest["known_evidence"], manifest["unknown_evidence"])
    visible = [report["condition_id"] for report in manifest["reports"] if report["condition_id"]]
    kind = PHASES[phase]
    actual = truth[query_id]["condition_id"]
    if (kind == "excluded") == (actual in visible):
        raise ValueError("Reference exclusion differs from the registered phase.")
    expected = "different" if kind == "excluded" else actual
    predicted = decision["condition_id"] if decision["outcome"] == "similar" else "different"
    if rows[0]["predicted_label"] != labels.get(predicted, predicted):
        raise ValueError("Evaluation label differs from the parsed decision.")
    return {"bundle": bundle, "manifest": manifest, "receipt": receipt, "decision": decision,
            "visible": visible, "phase": kind, "expected": expected, "truth": actual,
            "predicted": predicted, "category": category(kind, expected, predicted)}


def contact_sheets(case, references, query):
    request = read_json(case["bundle"] / "02_model/request.json")
    images = [part["image_url"] for message in request["messages"]
              if isinstance(message["content"], list)
              for part in message["content"] if part["type"] == "image_url"]
    sheets = read_json(case["bundle"] / "02_model/image-manifest.json")
    if [image_hash(image["url"]) for image in images] != [sheet["sha256"] for sheet in sheets]:
        raise ValueError("Contact-sheet manifest differs from the transmitted images.")
    owners = {report["id"]: report["condition_id"] for report in case["manifest"]["reports"]}
    exported = []
    for sheet, image in zip(sheets, images, strict=True):
        components = []
        for component in sheet["components"]:
            owner = component["id"].split(".", 1)[0]
            record = query if owners[owner] is None else references[owners[owner]]
            if component["original_sha256"] not in record["figureHashes"].values():
                raise ValueError("Model contact sheet uses an unpublished figure.")
            components.append({key: component[key] for key in (
                "id", "title", "original_sha256", "width", "height")})
        exported.append({"sha256": sheet["sha256"], "detail": image["detail"],
                         "components": components})
    for owner, condition in owners.items():
        record = query if condition is None else references[condition]
        cited = {item["original_sha256"] for sheet in exported for item in sheet["components"]
                 if item["id"].startswith(owner + ".")}
        if cited != set(record["figureHashes"].values()):
            raise ValueError("A model-facing report lacks complete published figures.")
    return request, exported


def export_inputs(case, case_id, request, sheets, output):
    messages = []
    for message in request["messages"]:
        if isinstance(message["content"], str):
            messages.append(message)
        else:
            messages.append({"role": message["role"], "content": [
                part if part["type"] == "text" else
                {"type": "image", "contact_sheet_sha256": image_hash(part["image_url"]["url"])}
                for part in message["content"]]})
    write_json(output / "inputs" / f"{case_id}.json", {
        "messages": messages, "response_format": request["response_format"],
        "reasoning_effort": request["reasoning_effort"],
        "max_completion_tokens": request["max_completion_tokens"], "contact_sheets": sheets,
        "source_request_sha256": case["receipt"]["request_sha256"],
        "publication": "Exact transmitted text and schema. Each image part is replaced by its "
        "contact-sheet hash; every sheet cell is published at full resolution under media/.",
    })
    write_json(output / "responses" / f"{case_id}.json", {
        "decision": case["decision"], "model": case["receipt"]["returned_model"],
        "source_request_sha256": case["receipt"]["request_sha256"],
        "source_response_sha256": case["receipt"]["response_sha256"],
        "publication": "Exact parsed decision; transport identifiers and cloud metadata omitted.",
    })


def distance_note(case, numeric_rows, conditions):
    path = case["bundle"] / "02_model/spectral-comparison.json"
    if path.exists():
        distances = read_json(path)["query_distance_db"]
        nearest = min(distances, key=distances.get)
        gap = min(value for key, value in read_json(path)["nearest_other_reference_db"].items()
                  if key in distances)
        text = (f"Welch distance supplied to the model: nearest {nearest} at "
                f"{distances[nearest]:.2f} dB")
        if case["phase"] != "excluded" and nearest == case["truth"]:
            text += ", the correct class"
        elif case["phase"] != "excluded":
            text += f"; correct {case['truth']} at {distances[case['truth']]:.2f} dB"
        return text + f". Closest pair of supplied references: {gap:.2f} dB."
    row = numeric_rows.get(case["bundle"].name)
    if row is None:
        return ""
    values = dict(zip(conditions, row["distances_db"], strict=True))
    nearest = min(values, key=values.get)
    correct = (", the correct class" if nearest == case["truth"] else
               f"; correct {case['truth']} at {values[case['truth']]:.2f} dB")
    return (f"Distances were not supplied to the model. Recorded numerical control: nearest "
            f"{nearest} at {values[nearest]:.2f} dB{correct}.")


def build_collections(output):
    datasets, rows, cases_extra, summaries = [], [], {}, []
    loaded = {}
    for spec in COLLECTIONS:
        folder = ROOT / "outputs" / spec["folder"]
        if spec["folder"] not in loaded:
            protocol, truth = registration(folder)
            references = {item["condition_id"]: export_record(folder, item, output)
                          | {"condition": item["condition_id"], "label": item["label"]}
                          for item in protocol["known"]}
            queries = {item["id"]: item for item in protocol["queries"]}
            loaded[spec["folder"]] = (protocol, truth, references, queries, {})
        protocol, truth, references, queries, records = loaded[spec["folder"]]
        labels = {item["condition_id"]: item["label"] for item in protocol["known"]}
        numeric = {}
        if (folder / "numeric-control.json").exists():
            numeric = {row["id"]: row for row in
                       read_json(folder / "numeric-control.json")["0"]["rows"]}
        conditions = [item["condition_id"] for item in protocol["known"]]
        collection_rows, query_records = [], {}
        for phase in spec["phases"]:
            evaluation = read_json(folder / spec["round"] / f"{phase}-evaluation.json")
            for row in evaluation["rows"]:
                query_id = row["id"]
                if query_id not in records:
                    records[query_id] = export_record(folder, queries[query_id], output)
                record = records[query_id] | {"truth": truth[query_id]["condition_id"]}
                query_records[query_id] = record
                case = load_case(folder, spec["round"], phase, query_id, truth, evaluation,
                                 labels)
                if case["visible"] != [c for c in conditions if c in case["visible"]]:
                    raise ValueError("Unexpected reference order.")
                case_id = f"{spec['key']}-{case['phase']}-{query_id}"
                request, sheets = contact_sheets(case, references, record)
                export_inputs(case, case_id, request, sheets, output)
                collection_rows.append({
                    "name": case_id, "dataset": spec["name"], "query_id": query_id,
                    "phase": case["phase"], "predicted": case["predicted"],
                    "expected": case["expected"], "category": case["category"]})
                acquisition = truth[query_id]
                cases_extra[case_id] = {
                    "explanation": case["decision"]["explanation"],
                    "responseLink": f"responses/{case_id}.json",
                    "inputLink": f"inputs/{case_id}.json",
                    "note": distance_note(case, numeric, conditions),
                    "attemptLabel": f"{METHODS[ROUNDS[(spec['folder'], spec['round'])]]} / "
                    + ("development" if case["phase"] == "development" else
                       "reserved window" if case["phase"] == "reserved" else "excluded-class test")
                    + f" / {acquisition.get('source_acquisition', '')}"
                    + (f" at {acquisition['offset_seconds']} s"
                       if "offset_seconds" in acquisition else ""),
                }
        counts = Counter(row["category"] for row in collection_rows)
        if dict(counts) != spec["expected"]:
            raise ValueError(f"{spec['key']} outcomes differ from the documented result: {counts}")
        summaries.append({"collection": spec["name"], "configuration": ROUNDS[
            (spec["folder"], spec["round"])], "decisions": len(collection_rows), **counts})
        rows.extend(collection_rows)
        datasets.append({"name": spec["name"], "references": list(references.values()),
                         "queries": list(query_records.values())})
    packed, cases = simple_review_data(datasets, rows)
    for case in cases:
        case.update(cases_extra[case["id"]])
    return packed, cases, summaries


def outcome_rows():
    audit = read_json(ROOT / "outputs/dsp-labeled-results-v1/case-audit.json")
    if len(audit) != 68:
        raise ValueError("Expected all 68 recorded labeled HTTP attempts.")
    rows = []
    for item in audit:
        parts = Path(item["bundle"].replace("\\", "/")).parts
        study, round_name, phase, query_id = parts[-4:]
        bundle = ROOT / "outputs" / study / round_name / phase / query_id
        receipt = read_json(bundle / "03_response/attempt.json")
        if (digest(bundle / "02_model/request.json") != item["request_sha256"]
                or digest(bundle / "03_response/response.json") != item["response_sha256"]
                or receipt["request_sha256"] != item["request_sha256"]):
            raise ValueError("Outcome audit differs from the recorded bundle.")
        distances = None
        if (bundle / "02_model/spectral-comparison.json").exists():
            distances = {key: round(value, 4) for key, value in read_json(
                bundle / "02_model/spectral-comparison.json")["query_distance_db"].items()}
        rows.append({
            "dataset": "Jin" if "jin" in study else "Ottawa", "study": study,
            "round": round_name, "configuration": ROUNDS[(study, round_name)],
            "phase": PHASES[phase], "query_id": query_id, "expected": item["expected"],
            "predicted": item["predicted"], "category": item["category"],
            "http_status": receipt.get("http_status"),
            "welch_distance_db_supplied": distances,
            "request_sha256": item["request_sha256"], "response_sha256": item["response_sha256"],
        })
    return rows


def numeric_controls():
    result = {}
    for study in ("dsp-jin-v1", "dsp-ottawa-v2"):
        data = read_json(ROOT / "outputs" / study / "numeric-control.json")
        result[study] = {f"development_nearest_above_{key}_hz":
                         f"{value['correct']}/{value['queries']}" for key, value in data.items()}
    reserved = 0
    folder = ROOT / "outputs/dsp-jin-v1/round-02/final"
    truth = read_json(ROOT / "outputs/dsp-jin-v1/sealed/truth.json")
    for bundle in sorted(folder.iterdir()):
        distances = read_json(bundle / "02_model/spectral-comparison.json")["query_distance_db"]
        reserved += min(distances, key=distances.get) == truth[bundle.name]["condition_id"]
    result["dsp-jin-v1"]["reserved_forced_nearest_recount"] = f"{reserved}/12"
    return result


def references_summary():
    result = {}
    for study, name in (("dsp-jin-v1", "Jin"), ("dsp-ottawa-v2", "Ottawa")):
        protocol, _ = registration(ROOT / "outputs" / study)
        result[name] = [{key: item[key] for key in (
            "condition_id", "label", "source_acquisition", "direction", "profile", "load")
            if key in item} for item in protocol["known"]]
    return result


def code_binding():
    recorded = {}
    for study in ("dsp-ottawa-v1", "dsp-ottawa-v2", "dsp-jin-v1"):
        protocol, _ = registration(ROOT / "outputs" / study)
        recorded[f"{study} registration runner"] = protocol["code_sha256"]
        for path in sorted((ROOT / "outputs" / study).glob("round-*/*/*/manifest.json")):
            hashes = read_json(path)["code_sha256"]
            for key, value in ((f"{study} {path.parts[-4]} similarity module",
                                hashes["similarity"]),
                               ("model transport helpers", hashes["azure_helpers"])):
                if recorded.setdefault(key, value) != value:
                    raise ValueError("One round used several code versions.")
    for key, value in read_json(ROOT / "outputs/dsp-jin-v1/reports/T01/manifest.json")[
            "code_sha256"].items():
        recorded[f"DSP report {key}"] = value
    candidates = sorted([*(ROOT / "src/modelmetis").glob("*.py"),
                         ROOT / "scripts/evaluate_dsp_similarity.py",
                         *(ROOT / "registered/simple-method").glob("*.py")])
    rows = []
    for use, value in recorded.items():
        files = [path.relative_to(ROOT).as_posix() for path in candidates
                 if code_matches(path, value)]
        rows.append({"use": use, "sha256": value, "repository_file": files[0] if files else None})
    return {"files": rows, "meaning": "Repository file whose content, up to line endings, has "
            "the recorded hash. Null means that exact version was not preserved; the exact "
            "transmitted requests and responses remain the evidence."}


def results_table(summaries):
    keys = ("Correct class", "Wrong class", "False rejection", "Correct rejection",
            "Wrong acceptance")
    body = []
    for item in summaries:
        known = sum(item.get(key, 0) for key in keys[:3])
        excluded = sum(item.get(key, 0) for key in keys[3:])
        cells = [html.escape(item["collection"]),
                 html.escape(METHODS[item["configuration"]]),
                 f"{item.get('Correct class', 0)}/{known}",
                 f"{item.get('Wrong class', 0)}/{known}",
                 f"{item.get('False rejection', 0)}/{known}",
                 f"{item.get('Correct rejection', 0)}/{excluded}" if excluded else "Not tested",
                 f"{item.get('Wrong acceptance', 0)}/{excluded}" if excluded else "Not tested"]
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return "\n".join(body)


def example_cards(cases):
    lookup = {case["id"]: case for case in cases}
    cards = []
    for identifier, expected, title, text in EXAMPLES:
        case = lookup[identifier]
        if case["category"] != expected:
            raise ValueError("Highlighted example differs from its recorded outcome.")
        cards.append(
            f'<a class="example" data-direction="{case["direction"]}" '
            f'href="audio-comparison/index.html#{identifier}"><span class="tag">'
            f'{html.escape(expected)}</span><strong>{html.escape(title)}</strong>'
            f'<span>{html.escape(text)}</span></a>')
    return "\n".join(cards)


def build(output):
    output = Path(output)
    comparison = output / "audio-comparison"
    if comparison.exists() or (output / "results").exists():
        raise ValueError("Generate into a new output directory.")
    packed, cases, summaries = build_collections(comparison)
    icons = read_json(TEMPLATES / "icons.json")
    payload = {
        "schema": 3, "datasets": packed, "cases": cases, "icons": icons,
        "views": [[key, OVERVIEW[0] if key == "overview" else VIEW_GUIDE[key][0]]
                  for key in VIEWS],
        "guide": {key: OVERVIEW[1] if key == "overview" else VIEW_GUIDE[key][1]
                  for key in VIEWS},
        "pageTitle": "ModelMetis / Simple method comparison", "compact": False,
        "defaultView": "welch", "deepLinks": True, "defaultCollection": "Jin: reports + distances",
        "defaultFilter": "all",
        "studyNotice": "Recorded decisions of the simple method. The system analyzes each "
        "recording into a DSP report; a general multimodal model studies the unknown report "
        "beside one report per known condition and names a condition or answers different. "
        "Each collection is one configuration with its own counts.",
        "displayScope": "The model studied these eight figures as contact-sheet cells together "
        "with the numerical measurements of each report.",
    }
    page = (TEMPLATES / "audio_comparison_simple.html").read_text(encoding="utf-8")
    page = page.replace("__THEME__", THEME).replace("__BASE_STYLE__", STYLE)
    page = page.replace("__DATA__", canonical_json(payload).decode().replace("<", "\\u003c"))
    page = page.replace("Audio comparison v14 / ModelMetis", payload["pageTitle"])
    page = reword(page)
    page = page.replace(
        '<div class="header-actions"></div>',
        '<div class="header-actions"><a href="../index.html">Method and results</a>'
        '<a href="https://github.com/faustinopalma/ModelMetis/blob/main/examples/'
        'audio-comparison/README.md">Sources and scope</a></div>')
    page = page.replace(
        '<span id="attribution"></span>',
        '<span id="attribution"></span> / <a href="https://github.com/faustinopalma/'
        'ModelMetis/blob/main/examples/audio-comparison/ATTRIBUTION.md">Attribution</a>')
    (comparison / "index.html").write_text(page, encoding="utf-8")
    write_json(comparison / "provenance.json", {
        "datasets": {name: {**metadata, "license": LICENSE_URL}
                     for name, metadata in DATASETS.items()},
        "records": [{"collection": dataset["name"], "record_id": record["id"],
                     "class": record.get("label", record.get("truth")),
                     "audio": record["audio"], "audio_sha256": record["audioHash"],
                     "figure_sha256": record["figureHashes"], "sample_rate": record["rate"],
                     "duration_seconds": record["duration"]}
                    for dataset in packed for record in [*dataset["references"],
                                                         *dataset["queries"]]],
        "decisions": len(cases), "collections": summaries,
        "generator": "scripts/publish_simple_method.py",
    })
    outcomes = outcome_rows()
    write_json(output / "results/simple-method-outcomes.json", outcomes)
    completed = [row for row in outcomes if row["category"] != "technical_failure"]
    by_config = Counter((row["dataset"], row["configuration"], row["phase"], row["category"])
                        for row in completed)
    write_json(output / "results/simple-method-summary.json", {
        "method": "One deterministic DSP report per known condition plus one unknown report; "
        "the model compares them and returns a known condition or different.",
        "configurations": METHODS, "collections": summaries,
        "outcome_counts": [{"dataset": key[0], "configuration": key[1], "phase": key[2],
                            "category": key[3], "count": value}
                           for key, value in sorted(by_config.items())],
        "http_attempts": len(outcomes), "completed_decisions": len(completed),
        "technical_failures": len(outcomes) - len(completed),
        "numerical_controls": numeric_controls(),
        "calibration": read_json(ROOT / "outputs/dsp-jin-v1/class-calibration.json"),
        "references": references_summary(), "code_binding": code_binding(),
        "limits": list(LIMITS),
    })
    template = (TEMPLATES / "method_index.html").read_text(encoding="utf-8")
    index = template.replace("__THEME__", THEME).replace("__BASE_STYLE__", STYLE)
    index = index.replace("__RESULT_ROWS__", results_table(summaries))
    index = index.replace("__EXAMPLES__", example_cards(cases))
    (output / "index.html").write_text(index, encoding="utf-8")
    seal(comparison)
    print(json.dumps({"output": str(output), "decisions": len(cases), "collections": summaries},
                     indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish the simple DSP-to-model evidence.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="New directory for a generated snapshot")
    action.add_argument("--seal", type=Path, help="Rewrite the manifest of an assembled root")
    args = parser.parse_args()
    if args.seal:
        seal(args.seal)
    else:
        build(args.output)
