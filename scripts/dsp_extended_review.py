import argparse
import html
import os
from collections import Counter
from pathlib import Path

from modelmetis.dsp_guide import VIEW_GUIDE
from modelmetis.dsp_report import STYLE, THEME, digest
from modelmetis.dsp_similarity import validate_result
from modelmetis.visual_audio import canonical_json
from scripts.audio_comparison import TEMPLATE, load_icons
from scripts.dsp_extended_experiment import read_json, write_json


def link(path, output):
    return html.escape(os.path.relpath(path, output).replace("\\", "/"), quote=True)


def validated_decisions(source):
    source = Path(source)
    registration = read_json(source / "registration.json")
    truth_path = source / "sealed/truth.json"
    if digest(truth_path) != registration["truth_sha256"]:
        raise ValueError("Registered truth changed.")
    truth = read_json(truth_path)
    rows = []
    for case in registration["cases"]:
        folder = source / case["name"]
        for filename, key in (
            ("request.json", "request_sha256"),
            ("contract.json", "contract_sha256"),
        ):
            if digest(folder / filename) != case[key]:
                raise ValueError("AI input binding failed.")
        receipt = read_json(folder / "attempt.json")
        if (
            receipt["status"] != "completed"
            or digest(folder / "response.json") != (receipt["response_sha256"])
            or receipt["request_sha256"] != case["request_sha256"]
        ):
            raise ValueError("AI output binding failed.")
        response = read_json(folder / "response.json")
        import json

        decision = json.loads(response["choices"][0]["message"]["content"])
        contract = read_json(folder / "contract.json")
        validate_result(decision, contract["known_evidence"], contract["unknown_evidence"])
        if decision != receipt["decision"]:
            raise ValueError("Saved decision differs from the actual response.")
        predicted = decision["condition_id"] if decision["outcome"] == "similar" else "different"
        expected = truth[case["name"]]
        if case["phase"] == "excluded":
            category = "Correct rejection" if predicted == "different" else "Wrong acceptance"
        else:
            category = (
                "Correct class"
                if predicted == expected
                else ("False rejection" if predicted == "different" else "Wrong class")
            )
        rows.append(
            {
                **case,
                "expected": expected,
                "predicted": predicted,
                "category": category,
                "receipt": receipt,
            }
        )
    return rows


def error_direction_summary(rows):
    counts = Counter(row["category"] for row in rows)
    if not rows or set(counts) - {
        "Correct class", "Correct rejection", "Wrong class", "Wrong acceptance", "False rejection"
    }:
        raise ValueError("Error-direction summary requires nonempty validated decisions.")
    unsafe = counts["Wrong class"] + counts["Wrong acceptance"]
    review = counts["False rejection"]
    return {
        "total": len(rows), "unsafeErrors": unsafe, "reviewErrors": review,
        "correct": counts["Correct class"] + counts["Correct rejection"],
        "errors": unsafe + review,
        "reviewDirected": review + counts["Correct rejection"],
        "accepted": len(rows) - review - counts["Correct rejection"],
        "routing": "different would route to review; human intervention was not executed",
    }


def error_direction(category):
    if category in {"Wrong class", "Wrong acceptance"}:
        return "wrong"
    if category == "False rejection":
        return "review"
    if category in {"Correct class", "Correct rejection"}:
        return "correct"
    raise ValueError("Unrecognized decision category.")


def simple_review_data(datasets, decisions):
    reviewed_datasets, cases = [], []
    for dataset in datasets:
        rows = [row for row in decisions if row["dataset"] == dataset["name"]]
        queries = {record["id"]: record for record in dataset["queries"]}
        references = dataset["references"]
        for row in rows:
            query = queries[row["query_id"]]
            correct = [record for record in references if record["condition"] == query["truth"]]
            chosen = [record for record in references if record["condition"] == row["predicted"]]
            if len(correct) != 1 or (row["predicted"] != "different" and len(chosen) != 1):
                raise ValueError("Each class choice requires an unambiguous reference.")
            excluded = row["phase"] == "excluded"
            visible = [record["id"] for record in references
                       if not excluded or record["condition"] != query["truth"]]
            if chosen and chosen[0]["id"] not in visible:
                raise ValueError("The model chose a reference excluded from its request.")
            cases.append({
                "id": row["name"], "dataset": dataset["name"], "queryId": query["id"],
                "correctReferenceId": correct[0]["id"],
                "modelReferenceId": chosen[0]["id"] if chosen else None,
                "modelOutcome": "other" if row["predicted"] == "different" else "class",
                "direction": error_direction(row["category"]), "category": row["category"],
                "expected": row["expected"], "correctClassExcluded": excluded,
                "visibleReferenceIds": visible,
            })
        query_ids = {row["query_id"] for row in rows}

        def review_record(record):
            return {key: record[key] for key in (
                "id", "audio", "figures", "duration", "rate", "audioHash", "figureHashes",
                "truth", "condition", "label", "viewMetadata") if key in record}

        reviewed_datasets.append({
            "name": dataset["name"],
            "references": [review_record(record) for record in references],
            "queries": [review_record(record) for record in dataset["queries"]
                        if record["id"] in query_ids],
        })
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Expected distinct, nonempty AI review cases.")
    return reviewed_datasets, cases


def build(source, ai_source, output, simplified=False):
    source, ai_source, output = Path(source), Path(ai_source), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_manifest = read_json(source / "manifest.json")
    for name, expected in source_manifest["files"].items():
        if digest(source / name) != expected:
            raise ValueError("Offline artifact binding failed.")
    decisions = validated_decisions(ai_source)
    direction = error_direction_summary(decisions)
    datasets = [read_json(source / name / "dataset.json") for name in ("Jin", "Ottawa")]
    for dataset in datasets:
        for record in [*dataset["references"], *dataset["queries"]]:
            record.pop("signatures", None)
        for query in dataset["queries"]:
            for row in decisions:
                if (
                    row["dataset"] == dataset["name"]
                    and row["query_id"] == query["id"]
                    and (row["phase"] == "known")
                ):
                    decision = row["receipt"]["decision"]
                    query["models"].insert(
                        0,
                        {
                            "round": "AI-all-diagrams",
                            "phase": "known",
                            "status": "completed",
                            "outcome": decision["outcome"],
                            "condition": decision["condition_id"],
                        },
                    )
    payload = {
        "schema": 2,
        "datasets": datasets,
        "icons": load_icons(),
        "views": [[key, value[0]] for key, value in VIEW_GUIDE.items()],
        "guide": {key: value[1] for key, value in VIEW_GUIDE.items()},
        "resultNoun": "Result",
        "defaultTrial": "AI-all-diagrams / known",
        "campaignSummary": direction,
        "fingerprint": digest(source / "manifest.json") + digest(ai_source / "registration.json"),
    }
    template = TEMPLATE
    if simplified:
        payload["datasets"], payload["cases"] = simple_review_data(datasets, decisions)
        template = Path(__file__).parent / "templates/audio_comparison_simple.html"
    page = (
        template.read_text(encoding="utf-8")
        .replace("__THEME__", THEME)
        .replace("__BASE_STYLE__", STYLE)
        .replace("__DATA__", canonical_json(payload).decode().replace("<", "\\u003c"))
    )
    page = page.replace(
        '<div class="header-actions">',
        '<div class="header-actions">'
        '<a href="results.html">AI results</a><a href="prompt.txt">Model prompt</a>',
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    prompt = read_json(ai_source / decisions[0]["name"] / "request.json")["messages"][0]["content"]
    (output / "prompt.txt").write_text(prompt, encoding="utf-8")
    table_rows, summary = [], []
    for dataset_name in ("Jin", "Ottawa"):
        selected = [row for row in decisions if row["dataset"] == dataset_name]
        counts = Counter(row["category"] for row in selected)
        known = sum(row["phase"] == "known" for row in selected)
        excluded = len(selected) - known
        summary.append(
            f"<tr><td>{dataset_name}</td><td>{counts['Correct class']}/{known}</td>"
            f"<td>{counts['Wrong class']}/{known}</td>"
            f"<td>{counts['False rejection']}/{known}</td>"
            f"<td>{counts['Correct rejection']}/{excluded}</td>"
            f"<td>{counts['Wrong acceptance']}/{excluded}</td></tr>"
        )
    for row in decisions:
        folder = ai_source / row["name"]
        category = html.escape(row["category"])
        operational = {
            "wrong": "Unacceptable: wrong class assigned",
            "review": "Acceptable direction: human review",
            "correct": "Correct decision",
        }[error_direction(row["category"])]
        table_rows.append(
            f"<tr data-direction='{error_direction(row['category'])}'><td>{row['dataset']}</td>"
            f"<td>{row['query_id']}</td><td>{row['phase']}</td>"
            f"<td>{row['expected']}</td><td>{row['predicted']}</td><td><strong>{category}</strong></td>"
            f"<td>{operational}</td>"
            f'<td><a href="{link(folder / "request.json", output)}">Exact request</a> / '
            f'<a href="{link(folder / "response.json", output)}">Raw response</a>'
            f"<details><summary>Explanation</summary><p>{html.escape(row['receipt']['decision']['explanation'])}</p></details></td></tr>"
        )
    known_cost = sum(row["receipt"].get("estimated_cost_usd") or 0 for row in decisions)
    unpriced = sum(row["receipt"].get("estimated_cost_usd") is None for row in decisions)
    result_page = (
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>All-diagram AI results</title>{THEME}<style>{STYLE}</style></head>"
        "<body><header><h1>All-diagram AI results</h1>"
        f"<p><strong>{direction['unsafeErrors']} of {direction['errors']} errors assign a wrong "
        f"class; {direction['reviewErrors']} would route to human review.</strong> "
        "The wrong-assignment requirement is not met.</p>"
        f"<p>{direction['unsafeErrors']}/{direction['total']} unacceptable decisions; "
        f"{direction['reviewErrors']}/{direction['total']} review-directed errors; "
        f"{direction['correct']}/{direction['total']} correct decisions. "
        "Human intervention was not executed. Validated structured decisions determine routing; "
        "uncertainty in the explanation does not override an assigned class.</p>"
        "<p>Previously consumed acquisitions; twelve query recordings each tested twice. "
        "Reference removal is not genuine unseen-fault validation. "
        "Two earlier HTTP 429 attempts produced no classification.</p>"
        f"<p>Priced usage estimate: USD {known_cost:.8f}; {unpriced} completed calls "
        "exceed the legacy short-context pricing guard and remain unpriced. "
        "The two rejected attempts have no usage receipt.</p>"
        '<nav><a href="index.html">Audio comparison</a><a href="prompt.txt">Diagram guide</a></nav>'
        "</header><main><div class='table-scroll'><table><tr><th>Dataset</th>"
        "<th>Correct known</th><th>Wrong class</th><th>False rejection</th>"
        "<th>Correct excluded</th><th>Wrong acceptance</th></tr>"
        + "".join(summary)
        + "</table></div><h2>Decisions</h2>"
        "<label>Outcome filter <select id='outcome-filter'>"
        "<option value='errors' selected>Errors only</option>"
        "<option value='wrong'>Wrong classification (unacceptable)</option>"
        "<option value='review'>Rejection for review (acceptable direction)</option>"
        "<option value='all'>All decisions</option></select></label>"
        "<p id='visible-count' aria-live='polite'></p>"
        "<div class='table-scroll'><table id='decisions-table'><tr><th>Dataset</th>"
        "<th>Query</th><th>Case</th><th>Expected</th><th>Observed</th><th>Result</th>"
        "<th>Operational direction</th><th>Evidence</th></tr>"
        + "".join(table_rows)
        + "</table></div></main><script>"
        "const filter=document.getElementById('outcome-filter');"
        "const rows=[...document.querySelectorAll('#decisions-table [data-direction]')];"
        "function filterResults(){let visible=0;for(const row of rows){"
        "const matches=filter.value==='all'||(filter.value==='errors'?"
        "row.dataset.direction!=='correct':row.dataset.direction===filter.value);"
        "row.hidden=!matches;if(matches)visible++;}"
        "document.getElementById('visible-count').textContent="
        "visible+' / '+rows.length+' decisions';}"
        "filter.addEventListener('change',filterResults);filterResults();"
        "</script></body></html>"
    )
    (output / "results.html").write_text(result_page, encoding="utf-8")
    write_json(
        output / "manifest.json",
        {
            "files": {
                name: digest(output / name) for name in ("index.html", "results.html", "prompt.txt")
            },
            "views": len(VIEW_GUIDE),
            "records": sum(len(dataset["references"]) + len(dataset["queries"])
                           for dataset in payload["datasets"]),
            "ai_decisions": len(decisions),
            "mode": "simple-ai-review" if simplified else "extended-review",
            "template_sha256": digest(template),
            "source_manifest_sha256": digest(source / "manifest.json"),
            "ai_registration_sha256": digest(ai_source / "registration.json"),
        },
    )
    print(f"Review: {output / 'index.html'}; AI results: {output / 'results.html'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audited all-diagram audio and AI review.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ai-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simple", action="store_true")
    args = parser.parse_args()
    build(args.source, args.ai_source, args.output, simplified=args.simple)
