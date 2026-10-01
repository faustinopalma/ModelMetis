import argparse
from pathlib import Path

from modelmetis.dsp_guide import VIEW_GUIDE
from modelmetis.dsp_report import STYLE, THEME, digest
from modelmetis.visual_audio import canonical_json
from scripts.audio_comparison import load_icons
from scripts.dsp_extended_experiment import read_json, write_json
from scripts.dsp_extended_review import link, simple_review_data, validated_decisions

DISPLAY_VIEWS = ("welch", "fft", "stft", "cepstrum")
REMOVED = {"ridge", "autocorrelation", "bands"}


def review_payload(datasets, decisions):
    rows = [row for row in decisions if row.get("arm") == "mask111"]
    if not rows or any(set(row["removed"]) != REMOVED for row in rows):
        raise ValueError("Expected the recorded triple-removal candidate.")
    packed, cases = simple_review_data(datasets, rows)
    by_name = {row["name"]: row for row in rows}
    for dataset in packed:
        for record in [*dataset["references"], *dataset["queries"]]:
            for field in ("figures", "figureHashes", "viewMetadata"):
                if field in record:
                    record[field] = {key: value for key, value in record[field].items()
                                     if key in DISPLAY_VIEWS}
            if set(record["figures"]) != set(DISPLAY_VIEWS):
                raise ValueError("Missing essential retained diagram.")
    for case in cases:
        row = by_name[case["id"]]
        case["attemptLabel"] = "Repeat" if row["block"] == "replicate" else "Primary"
        case["explanation"] = row["receipt"]["decision"]["explanation"]
        matched = [other for other in rows if other["source_case"] == row["source_case"]]
        predictions = {other["predicted"] for other in matched}
        case["repeatWarning"] = (
            "Identical-request results disagree. Candidate not approved."
            if len(predictions) > 1 else ""
        )
    cases.sort(key=lambda case: ({"wrong": 0, "review": 1, "correct": 2}[case["direction"]],
                                 case["dataset"], case["queryId"], case["id"]))
    return {
        "schema": 3, "datasets": packed, "cases": cases,
        "views": [[key, VIEW_GUIDE[key][0]] for key in DISPLAY_VIEWS],
        "guide": {key: VIEW_GUIDE[key][1] for key in DISPLAY_VIEWS},
        "pageTitle": "Pruned comparison / v15", "compact": True, "defaultView": "welch",
        "studyNotice": "Experimental mask111 / bands, autocorrelation and dominant ridge removed "
        "/ 8 primary decisions + 2 repeats / not approved",
        "displayScope": "Four retained diagrams shown; the model received 23. Display selection "
        "does not change the tested pipeline.",
    }


def build(source, experiment, output):
    source, experiment, output = Path(source), Path(experiment), Path(output)
    decisions = validated_decisions(experiment)
    selected = [row for row in decisions if row.get("arm") == "mask111"]
    if len(selected) != 10 or sum(row["block"] == "replicate" for row in selected) != 2:
        raise ValueError("Expected all eight primary candidate cases and both repeats.")
    manifest = read_json(source / "manifest.json")
    datasets = []
    for name in ("Jin", "Ottawa"):
        path = source / name / "dataset.json"
        if digest(path) != manifest["files"][f"{name}/dataset.json"]:
            raise ValueError("Bound audio/figure dataset changed.")
        datasets.append(read_json(path))
    payload = review_payload(datasets, decisions)
    payload["icons"] = load_icons()
    payload["fingerprint"] = digest(experiment / "registration.json")
    for case in payload["cases"]:
        case["responseLink"] = link(experiment / case["id"] / "response.json", output)
    template = Path(__file__).parent / "templates/audio_comparison_simple.html"
    page = template.read_text(encoding="utf-8")
    page = page.replace("__THEME__", THEME).replace("__BASE_STYLE__", STYLE)
    page = page.replace("__DATA__", canonical_json(payload).decode().replace("<", "\\u003c"))
    page = page.replace("Audio comparison v14 / ModelMetis", payload["pageTitle"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "index.html").write_text(page, encoding="utf-8")
    write_json(output / "manifest.json", {
        "files": {"index.html": digest(output / "index.html")},
        "display_views": list(DISPLAY_VIEWS), "removed_views": sorted(REMOVED),
        "model_view_count": 23, "primary_decisions": 8, "repeats": 2,
        "policy_adopted": False, "experiment_sha256": digest(experiment / "registration.json"),
        "source_manifest_sha256": digest(source / "manifest.json"),
        "template_sha256": digest(template), "generator_sha256": digest(__file__),
    })
    print(f"Pruned review: {output / 'index.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Essential recorded pruning review.")
    parser.add_argument("--source", type=Path, default=Path("outputs/dsp-extended-v1"))
    parser.add_argument("--experiment", type=Path, default=Path("outputs/dsp-pruning-cross-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.experiment, args.output)