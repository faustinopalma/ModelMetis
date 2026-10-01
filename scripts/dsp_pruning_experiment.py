import argparse
import base64
import copy
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from itertools import product
from pathlib import Path

from PIL import Image, ImageDraw

from modelmetis.dsp_guide import VIEW_GUIDE, interpretation_prompt
from modelmetis.dsp_report import digest
from modelmetis.visual_audio import canonical_json
from scripts import dsp_extended_ai as runner
from scripts.audio_comparison import ROOT, data_url
from scripts.dsp_extended_experiment import read_json, write_json
from scripts.dsp_extended_review import validated_decisions

FACTORS = ("ridge", "autocorrelation", "bands")
ALLOWED_REMOVALS = {*FACTORS, "spectral_kurtosis"}
BASE_FIELDS = {"bands": "bands", "autocorrelation": "autocorrelation"}


def variants():
    return [
        {
            "name": "mask" + "".join(str(value) for value in bits),
            "removed": [view for view, flag in zip(FACTORS, bits, strict=True) if flag],
        }
        for bits in product((0, 1), repeat=3)
    ]


def masked_sheet(url, cells, removed):
    payload = base64.b64decode(url.split(",", 1)[1], validate=True)
    with Image.open(io.BytesIO(payload)) as original:
        image = original.convert("RGB")
        if image.size != (2400, 1520) or len(cells) > 16:
            raise ValueError("Unexpected registered contact-sheet layout.")
        drawer = ImageDraw.Draw(image)
        for index, identifier in enumerate(cells):
            if identifier.rsplit(".", 1)[-1] in removed:
                left, top = index % 4 * 600, index // 4 * 380
                drawer.rectangle((left, top, left + 599, top + 379), fill="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return data_url(buffer.getvalue(), "image/png")


def prune_body(original, removed):
    removed = set(removed)
    if not removed.issubset(ALLOWED_REMOVALS):
        raise ValueError("Unregistered pruning factor.")
    body = copy.deepcopy(original)
    if len(body["messages"]) != 2 or body["messages"][1]["role"] != "user":
        raise ValueError("Expected a fresh source request without prior model replies.")
    retained = [key for key in VIEW_GUIDE if key not in removed]
    introduction = interpretation_prompt().split("DIAGRAM READING GUIDE")[0]
    body["messages"][0]["content"] = (
        introduction
        + "DIAGRAM READING GUIDE\n"
        + "\n".join(f"{key} / {VIEW_GUIDE[key][0]}: {VIEW_GUIDE[key][1]}" for key in retained)
        + (
            "\nMATCHED REVIEW PROTOCOL: First assess which supplied reference diagrams distinguish "
            "the known conditions. Then inspect the query and compare EVERY supplied reference. "
            "Inspect every supplied view, not just initial favorites. Empty contact-sheet cells "
            "are deliberately not supplied; do not infer their content. In explanation, summarize "
            "your initial reference priorities, final decisive views, strongest counterevidence "
            "and whether measurements, images or nearest-reference controls drive the decision. "
            "Provide concise observable findings, not private reasoning. Return similar and the "
            "best-supported condition_id when known similarity is supported; return different with "
            "null condition_id when all supplied conditions are substantially different. Include "
            "one comparison per supplied condition, citing that reference and the query using "
            "only evidence IDs present in this request. No calibrated acceptance threshold is "
            "supplied. A nearest reference is not sufficient evidence of acceptance."
        )
    )
    cells = None
    for part in body["messages"][1]["content"]:
        if part["type"] == "text":
            metadata = json.loads(part["text"])
            if "numerical_control" in metadata:
                for key in removed:
                    metadata["numerical_control"].pop(key, None)
            if "report" in metadata:
                for key in removed:
                    metadata["extensions"].pop(key, None)
                for channel in metadata["report"]["channels"]:
                    for interval in channel["intervals"]:
                        for key in removed:
                            if key in BASE_FIELDS:
                                interval["measurements"].pop(BASE_FIELDS[key], None)
                metadata["numerical_summary"] = (
                    "Supplied view metadata and measurements; curve extrema/largest bins and "
                    "map summaries. Missing views provide no evidence."
                )
            if "cell_evidence_ids_row_major" in metadata:
                cells = list(metadata["cell_evidence_ids_row_major"])
                metadata["cell_evidence_ids_row_major"] = [
                    identifier if identifier.rsplit(".", 1)[-1] not in removed else None
                    for identifier in cells
                ]
            part["text"] = canonical_json(metadata).decode()
        elif part["type"] == "image_url":
            if cells is None:
                raise ValueError("Image lacks a bound cell manifest.")
            part["image_url"]["url"] = masked_sheet(part["image_url"]["url"], cells, removed)
            cells = None
        else:
            raise ValueError("Unexpected source content type.")
    body["max_completion_tokens"] = 8192
    return body


def pruned_contract(original, removed):
    return {
        "known_evidence": {
            condition: [
                identifier
                for identifier in identifiers
                if identifier.rsplit(".", 1)[-1] not in removed
            ]
            for condition, identifiers in original["known_evidence"].items()
        },
        "unknown_evidence": [
            identifier
            for identifier in original["unknown_evidence"]
            if identifier.rsplit(".", 1)[-1] not in removed
        ],
    }


def schedule():
    jobs = []
    arms = variants()
    for block, cases, selected_arms in (
        (
            "factorial",
            [
                f"Ottawa-{phase}-{query}"
                for query in ("D03", "D07")
                for phase in ("known", "excluded")
            ],
            arms,
        ),
        (
            "regression",
            [
                f"{dataset}-{phase}-{query}"
                for dataset, query in (("Ottawa", "D01"), ("Jin", "T01"))
                for phase in ("known", "excluded")
            ],
            [arms[0], arms[-1]],
        ),
        (
            "targeted",
            [f"Ottawa-{phase}-D07" for phase in ("known", "excluded")],
            [{"name": "no-sk", "removed": ["spectral_kurtosis"]}],
        ),
        (
            "replicate",
            [f"Ottawa-{phase}-D03" for phase in ("known", "excluded")],
            [arms[0], arms[-1]],
        ),
    ):
        for case in cases:
            for arm in selected_arms:
                jobs.append(
                    {
                        "name": f"{block}-{case}-{arm['name']}",
                        "source_case": case,
                        "block": block,
                        "arm": arm["name"],
                        "removed": arm["removed"],
                    }
                )
    priority = {"regression-Jin-known-T01-mask000": 0, "factorial-Ottawa-known-D03-mask000": 1}
    jobs.sort(
        key=lambda job: (
            priority.get(job["name"], 2),
            hashlib.sha256(("crossed-pruning-v1:" + job["name"]).encode()).hexdigest(),
        )
    )
    if len(jobs) != 46 or len({job["name"] for job in jobs}) != 46:
        raise ValueError("Expected the frozen 46-decision design.")
    return jobs


def verify_removal(body, contract, removed):
    known = set().union(*map(set, contract["known_evidence"].values()))
    allowed = known | set(contract["unknown_evidence"])
    if any(identifier.rsplit(".", 1)[-1] in removed for identifier in allowed):
        raise ValueError("Removed view retained in citation contract.")
    for key in removed:
        if f"\n{key} / " in body["messages"][0]["content"]:
            raise ValueError("Removed view retained in guide.")
    for part in body["messages"][1]["content"]:
        if part["type"] != "text":
            continue
        metadata = json.loads(part["text"])
        if any(key in metadata.get("numerical_control", {}) for key in removed):
            raise ValueError("Removed distance control retained.")
        if "report" in metadata:
            if any(key in metadata["extensions"] for key in removed):
                raise ValueError("Removed extension retained.")
            for channel in metadata["report"]["channels"]:
                for interval in channel["intervals"]:
                    if any(
                        BASE_FIELDS[key] in interval["measurements"]
                        for key in removed
                        if key in BASE_FIELDS
                    ):
                        raise ValueError("Removed original measurement retained.")
        if any(
            identifier and identifier.rsplit(".", 1)[-1] in removed
            for identifier in metadata.get("cell_evidence_ids_row_major", [])
        ):
            raise ValueError("Removed image cell manifest retained.")


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    previous = {row["name"]: row for row in validated_decisions(source)}
    jobs = schedule()
    output.mkdir(parents=True, exist_ok=False)
    settings = read_json(source / "settings.json")
    settings.update(
        max_completion_tokens=8192,
        max_real_requests=len(jobs),
        request_process_timeout_seconds=300,
        run_deadline_seconds=7200,
    )
    write_json(output / "settings.json", settings)
    truth, cases, duplicates = {}, [], {}
    sources = {}
    for job in jobs:
        row = previous[job["source_case"]]
        if job["source_case"] not in sources:
            sources[job["source_case"]] = (
                read_json(source / row["name"] / "request.json"),
                read_json(source / row["name"] / "contract.json"),
            )
        original, original_contract = sources[job["source_case"]]
        body = prune_body(original, job["removed"])
        contract = pruned_contract(original_contract, job["removed"])
        verify_removal(body, contract, job["removed"])
        folder = output / job["name"]
        folder.mkdir()
        write_json(folder / "request.json", body)
        write_json(folder / "contract.json", contract)
        request_hash = digest(folder / "request.json")
        key = (job["source_case"], job["arm"])
        if key in duplicates and duplicates[key] != request_hash:
            raise ValueError("Replicate request bytes differ.")
        duplicates[key] = request_hash
        cases.append(
            {
                **job,
                **{key: row[key] for key in ("dataset", "phase", "query_id")},
                "request_sha256": request_hash,
                "contract_sha256": digest(folder / "contract.json"),
                "source_request_sha256": row["request_sha256"],
                "images": sum(
                    part["type"] == "image_url" for part in body["messages"][1]["content"]
                ),
                "request_bytes": (folder / "request.json").stat().st_size,
            }
        )
        truth[job["name"]] = row["expected"]
        print(f"Registered {len(cases)}/46: {job['name']}", flush=True)
    (output / "sealed").mkdir()
    write_json(output / "sealed/truth.json", truth)
    protocol = ROOT / "docs/DSP_PRUNING_PROTOCOL.md"
    (output / "protocol.md").write_bytes(protocol.read_bytes())
    modules = [
        Path(__file__),
        Path(runner.__file__),
        Path(runner.dsp_inference.__file__),
        Path(runner.dsp_similarity.__file__),
        ROOT / "src/modelmetis/dsp_guide.py",
    ]
    write_json(
        output / "registration.json",
        {
            "schema": 1,
            "cases": cases,
            "max_attempts": len(jobs),
            "spending_cap_usd": None,
            "authorization": "User requests crossed pruning tests and a later clean evaluation.",
            "protocol_sha256": digest(output / "protocol.md"),
            "code_sha256": {str(path.relative_to(ROOT)): digest(path) for path in modules},
            "settings_sha256": digest(output / "settings.json"),
            "truth_sha256": digest(output / "sealed/truth.json"),
            "source_registration_sha256": digest(source / "registration.json"),
            "factor_order": list(FACTORS),
            "cases_by_block": dict(Counter(job["block"] for job in jobs)),
            "stop_rule": "Stop on technical failure; one HTTP attempt per job, no automatic retry.",
            "final_evaluation": "Not executed. No acquisition from this study is a clean holdout.",
            "decision_schema": "Same binary schema across arms; no prior model reply.",
        },
    )
    return {"registered": len(cases), "unique_requests": len(set(duplicates.values()))}


def run_batch(output, limit):
    output = Path(output)
    registration = runner.verify(output)
    completed = 0
    for case in registration["cases"]:
        attempt = output / case["name"] / "attempt.json"
        if attempt.exists():
            if read_json(attempt)["status"] != "completed":
                raise ValueError("A failed attempt blocks this campaign; preserve and diagnose it.")
            continue
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.dsp_extended_ai",
                "one",
                "--output",
                str(output),
                "--case",
                case["name"],
            ],
            timeout=300,
            capture_output=True,
            text=True,
            check=False,
        )
        receipt = read_json(attempt) if attempt.exists() else {"status": "worker_failed"}
        decision = receipt.get("decision", {})
        print(
            json.dumps(
                {
                    "case": case["name"],
                    "status": receipt["status"],
                    "outcome": decision.get("outcome"),
                    "condition": decision.get("condition_id"),
                    "seconds": receipt.get("elapsed_seconds"),
                    "error": receipt.get("error"),
                }
            ),
            flush=True,
        )
        if process.returncode or receipt["status"] != "completed":
            raise RuntimeError("Technical failure retained; no subsequent job was sent.")
        completed += 1
        if completed >= limit:
            break
    return {"new_completed": completed}


def counts(rows):
    categories = Counter(row["outcome"] for row in rows)
    return {
        "total": len(rows),
        "correct_known": categories["correct_known"],
        "correct_rejection": categories["correct_rejection"],
        "wrong_class": categories["wrong_class"],
        "wrong_acceptance": categories["wrong_acceptance"],
        "false_rejection": categories["false_rejection"],
        "technical_failure": categories["technical_failure"],
    }


def evaluate(output):
    output = Path(output)
    registration = runner.verify(output)
    raw_rows = runner.evaluate(output)
    for case in registration["cases"]:
        folder = output / case["name"]
        if not (folder / "attempt.json").exists():
            continue
        receipt = read_json(folder / "attempt.json")
        if receipt["status"] != "completed":
            continue
        if digest(folder / "response.json") != receipt["response_sha256"]:
            raise ValueError("Raw response changed.")
        actual = json.loads(read_json(folder / "response.json")["choices"][0]["message"]["content"])
        if actual != receipt["decision"]:
            raise ValueError("Stored decision differs from raw model response.")
        contract = read_json(folder / "contract.json")
        runner.validate_result(actual, contract["known_evidence"], contract["unknown_evidence"])
    factorial = [row for row in raw_rows if row["block"] == "factorial"]
    primary = [row for row in raw_rows if row["block"] != "replicate"]
    transitions = []
    for row in primary:
        controls = [
            control
            for control in primary
            if control["source_case"] == row["source_case"] and control["arm"] == "mask000"
        ]
        if len(controls) == 1:
            transitions.append(
                {
                    "case": row["source_case"],
                    "arm": row["arm"],
                    "control": controls[0]["outcome"],
                    "outcome": row["outcome"],
                }
            )
    repeats = []
    for row in raw_rows:
        if row["block"] != "replicate":
            continue
        originals = [
            other
            for other in factorial
            if other["source_case"] == row["source_case"] and other["arm"] == row["arm"]
        ]
        if len(originals) == 1:
            repeats.append(
                {
                    "case": row["source_case"],
                    "arm": row["arm"],
                    "first": originals[0].get("predicted"),
                    "repeat": row.get("predicted"),
                    "same": originals[0].get("predicted") == row.get("predicted"),
                }
            )
    arms = {
        arm["name"]: counts([row for row in factorial if row["arm"] == arm["name"]])
        for arm in variants()
    }
    summary = {
        "registered": len(registration["cases"]),
        "completed": sum(row["status"] == "completed" for row in raw_rows),
        "factorial": arms,
        "regression": {
            arm: counts(
                [row for row in raw_rows if row["block"] == "regression" and row["arm"] == arm]
            )
            for arm in ("mask000", "mask111")
        },
        "targeted": counts([row for row in raw_rows if row["block"] == "targeted"]),
        "transitions": transitions,
        "replicates": repeats,
        "final_test_executed": False,
        "pruning_policy_adopted": False,
    }
    write_json(output / "crossed-results.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Matched crossed DSP pruning experiment.")
    parser.add_argument("action", choices=("prepare", "run", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("outputs/dsp-extended-ai-v4"))
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args.source, args.output)
    elif args.action == "run":
        result = run_batch(args.output, args.limit)
    else:
        result = evaluate(args.output)
    print(json.dumps(result), flush=True)
