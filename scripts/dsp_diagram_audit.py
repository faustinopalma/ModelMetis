import argparse
import copy
import json
import time
from collections import Counter
from pathlib import Path

import httpx
import jsonschema

from modelmetis import dsp_inference
from modelmetis.dsp_guide import VIEW_GUIDE
from modelmetis.dsp_report import digest
from modelmetis.dsp_similarity import decision_schema, validate_result
from modelmetis.visual_audio import canonical_json
from scripts.audio_comparison import ROOT
from scripts.dsp_extended_experiment import read_json, write_json
from scripts.dsp_extended_review import validated_decisions


def strict_object(properties):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def audit_schema(conditions, stage):
    text = {"type": "string"}
    strings = {"type": "array", "items": text}
    view = strict_object(
        {
            "priority": {"type": "string", "enum": ["high", "medium", "low", "unavailable"]},
            "finding": text,
            "evidence_ids": strings,
        }
    )
    if stage == "decision":
        view["properties"].update(
            {
                "favored_condition": {"type": ["string", "null"], "enum": [*conditions, None]},
                "effect": {
                    "type": "string",
                    "enum": ["supports", "contradicts", "neutral", "unavailable"],
                },
            }
        )
        view["required"] = list(view["properties"])
    properties = {
        "diagram_review": strict_object({key: {"$ref": "#/$defs/diagram"} for key in VIEW_GUIDE}),
        "most_informative": {
            "type": "array",
            "items": {"type": "string", "enum": list(VIEW_GUIDE)},
        },
        "limitations": text,
    }
    if stage == "decision":
        properties.update(
            {
                "decision": decision_schema(conditions)["json_schema"]["schema"],
                "decisive_diagrams": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(VIEW_GUIDE)},
                },
                "decision_basis": text,
                "counterevidence": text,
                "priority_changes": text,
            }
        )
    schema = strict_object(properties)
    schema["$defs"] = {"diagram": view}
    return {
        "type": "json_schema",
        "json_schema": {"name": "diagram_audit_" + stage, "strict": True, "schema": schema},
    }


def validate_audit(result, contract, stage):
    known = contract["known_evidence"]
    jsonschema.validate(result, audit_schema(known, stage)["json_schema"]["schema"])
    references = set().union(*[set(values) for values in known.values()])
    query = set(contract["unknown_evidence"]) if stage == "decision" else set()
    for key, entry in result["diagram_review"].items():
        citations = set(entry["evidence_ids"])
        reference_figures = {value for value in references if value.endswith("." + key)}
        query_figures = {value for value in query if value.endswith("." + key)}
        if (
            not entry["finding"].strip()
            or not citations
            or not citations.issubset(references | query)
            or not citations.intersection(reference_figures)
            or (stage == "decision" and not citations.intersection(query_figures))
        ):
            raise ValueError("Every diagram needs its own valid reference/query citations.")
        if key in {"orders", "synchronous"} and entry["priority"] != "unavailable":
            raise ValueError("Independent RPM is absent; rotational views are unavailable.")
        if stage == "decision" and entry["priority"] == "unavailable":
            if entry["effect"] != "unavailable" or entry["favored_condition"] is not None:
                raise ValueError("Unavailable diagrams cannot support a class.")
    for field in ["most_informative"] + (["decisive_diagrams"] if stage == "decision" else []):
        ranked = result[field]
        if (
            len(ranked) > 5
            or len(ranked) != len(set(ranked))
            or any(result["diagram_review"][key]["priority"] == "unavailable" for key in ranked)
        ):
            raise ValueError("Rank at most five distinct available diagrams.")
    if stage == "decision":
        validate_result(result["decision"], known, contract["unknown_evidence"])
    return result


def reference_only_body(original, contract):
    body = copy.deepcopy(original)
    parts = body["messages"][1]["content"]
    header = json.loads(parts[0]["text"])
    query_identifier = header.pop("query")
    reference_parts = [{"type": "text", "text": canonical_json(header).decode()}]
    reference_records = 0
    for part in parts[1:]:
        if part["type"] == "text":
            metadata = json.loads(part["text"])
            if "numerical_control" in metadata:
                continue
            if "report" in metadata:
                if metadata["report"]["id"] == query_identifier:
                    break
                reference_records += 1
        reference_parts.append(part)
    if reference_records != len(contract["known_evidence"]):
        raise ValueError("Reference-only survey must contain every reference and no query.")
    body["messages"] = [
        {
            "role": "system",
            "content": original["messages"][0]["content"].split("\nEXPERIMENT RESPONSE CONTRACT:")[
                0
            ]
            + "\nREFERENCE-ONLY SURVEY: Before seeing or classifying any query, inspect ALL 26 "
            "diagram types for ALL supplied references. For each type report one concise "
            "observable finding, its figure IDs and high/medium/low/unavailable priority "
            "for distinguishing these references. Rank at most five most informative types. "
            "Predictiveness is a tentative hypothesis: one example per class cannot establish "
            "generalization. Treat absent RPM and unreadable/masked content explicitly; never "
            "invent features. Separate actual between-reference differences from generic fault "
            "theory and correlated transforms. No query or query distances are supplied. "
            "Return concise auditable findings, not private reasoning or a classification.",
        },
        {"role": "user", "content": reference_parts},
    ]
    body["response_format"] = audit_schema(contract["known_evidence"], "survey")
    body["max_completion_tokens"] = 8192
    return body


def decision_body(original, contract, survey):
    body = copy.deepcopy(original)
    body["messages"][0]["content"] += (
        "\nDIAGRAM AUDIT: A separate reference-only survey was completed before this query "
        "was supplied. Its frozen output follows. Inspect ALL 26 diagram types for the query "
        "and ALL supplied references, not just the prior favorites. Report a concise visible "
        "finding for every type with exact reference and query figure IDs, updated priority, "
        "favored_condition (relative resemblance, not acceptance) and effect on your final "
        "decision: supports/contradicts/neutral/unavailable. Select at most five informative "
        "and decisive diagram types. Explain the final decision's observable basis, strongest "
        "counterevidence and any changed priorities. An unavailable diagram cannot favor a "
        "class. Numeric nearest-reference distances are controls, not calibrated acceptance "
        "thresholds or independent confirmation. Explicitly say if numerical controls rather "
        "than visual observations drive the decision. Keep the original binary decision "
        "contract under decision. Do not infer an actual unknown label. Do not claim the "
        "survey established predictive accuracy. Return findings, not private reasoning."
    )
    body["messages"][1]["content"].insert(
        0,
        {
            "type": "text",
            "text": "FROZEN REFERENCE-ONLY SURVEY:\n" + canonical_json(survey).decode(),
        },
    )
    body["response_format"] = audit_schema(contract["known_evidence"], "decision")
    body["max_completion_tokens"] = 12288
    return body


def select_cases(rows):
    selected = []
    for dataset, categories in (
        ("Jin", ["Correct class"]),
        ("Ottawa", ["Correct class", "Wrong class", "False rejection"]),
    ):
        for category in categories:
            candidates = sorted(
                (
                    row
                    for row in rows
                    if row["dataset"] == dataset
                    and row["phase"] == "known"
                    and row["category"] == category
                ),
                key=lambda row: row["query_id"],
            )
            if not candidates:
                raise ValueError("Missing prespecified outcome stratum.")
            query_id = candidates[0]["query_id"]
            paired = [
                row for row in rows if row["dataset"] == dataset and row["query_id"] == query_id
            ]
            if len(paired) != 2 or {row["phase"] for row in paired} != {"known", "excluded"}:
                raise ValueError("Each selected acquisition needs the registered pair.")
            selected.extend(sorted(paired, key=lambda row: row["phase"] != "known"))
    return selected


def adopt_result(source, folder, settings, stage):
    source, folder = Path(source), Path(folder)
    receipt = read_json(source / "attempt.json")
    if (receipt.get("http_status") != 200
            or digest(source / "response.json") != receipt["response_sha256"]
            or digest(source / "request.json") != receipt["request_sha256"]
            or digest(folder / "request.json") != receipt["request_sha256"]
            or digest(folder / "contract.json") != digest(source / "contract.json")):
        raise ValueError("Reuse requires identical bound inputs and raw response.")
    envelope = read_json(source / "response.json")
    choices = envelope.get("choices", [])
    if (len(choices) != 1 or choices[0].get("finish_reason") != "stop"
            or envelope.get("model") not in {
                settings["model"], settings["model"] + "-" + settings["version"]}
            or choices[0]["message"].get("refusal")):
        raise ValueError("Cannot reuse incomplete or mismatched completion.")
    result = validate_audit(json.loads(choices[0]["message"]["content"]),
                            read_json(folder / "contract.json"), stage)
    for filename in ("response.json", "attempt.json"):
        destination = "source-attempt.json" if filename == "attempt.json" else filename
        (folder / destination).write_bytes((source / filename).read_bytes())
    restored = {key: value for key, value in receipt.items() if key not in {"error", "error_type"}}
    write_json(folder / "attempt.json", {**restored, "status": "completed", "http_attempts": 0,
        "result": result, "reused_from": str(source),
        "source_attempt_sha256": digest(source / "attempt.json"),
        "validation_note": "Revalidated existing response; additional valid citations may "
        "accompany required same-view figure citations. Original receipt retained."})
    return {"name": folder.name, "stage": stage, "source": str(source),
            "source_attempt_sha256": digest(source / "attempt.json")}


def prepare(source, output, resume_source=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    rows = select_cases(validated_decisions(source))
    output.mkdir(parents=True, exist_ok=False)
    settings = read_json(source / "settings.json")
    settings.update(max_completion_tokens=12288, request_process_timeout_seconds=360)
    write_json(output / "settings.json", settings)
    jobs, surveys, selected, truth, reused = [], set(), [], {}, []
    for row in rows:
        original = read_json(source / row["name"] / "request.json")
        contract = read_json(source / row["name"] / "contract.json")
        survey = reference_only_body(original, contract)
        import hashlib

        survey_id = "survey-" + hashlib.sha256(canonical_json(survey)).hexdigest()[:16]
        if survey_id not in surveys:
            surveys.add(survey_id)
            folder = output / survey_id
            folder.mkdir()
            write_json(folder / "request.json", survey)
            write_json(folder / "contract.json", {**contract, "unknown_evidence": []})
            if resume_source and (Path(resume_source) / survey_id / "attempt.json").exists():
                reused.append(adopt_result(Path(resume_source) / survey_id, folder, settings,
                                           "survey"))
            jobs.append(
                {
                    "name": survey_id,
                    "stage": "survey",
                    "dataset": row["dataset"],
                    "request_sha256": digest(folder / "request.json"),
                    "contract_sha256": digest(folder / "contract.json"),
                }
            )
        folder = output / row["name"]
        folder.mkdir()
        write_json(folder / "original.json", original)
        write_json(folder / "contract.json", contract)
        if resume_source and (Path(resume_source) / row["name"] / "attempt.json").exists():
            survey_folder = output / survey_id
            frozen = completed_result(survey_folder,
                                      read_json(survey_folder / "contract.json"), "survey")
            write_json(folder / "request.json", decision_body(original, contract, frozen))
            write_json(folder / "request-binding.json", {
                "request_sha256": digest(folder / "request.json"),
                "survey_response_sha256": digest(survey_folder / "response.json"),
                "original_sha256": digest(folder / "original.json"),
            })
            reused.append(adopt_result(Path(resume_source) / row["name"], folder, settings,
                                       "decision"))
        jobs.append(
            {
                "name": row["name"],
                "stage": "decision",
                "dataset": row["dataset"],
                "phase": row["phase"],
                "query_id": row["query_id"],
                "survey": survey_id,
                "original_sha256": digest(folder / "original.json"),
                "contract_sha256": digest(folder / "contract.json"),
            }
        )
        selected.append(
            {
                key: row[key]
                for key in ("name", "dataset", "query_id", "phase", "predicted", "category")
            }
        )
        truth[row["name"]] = row["expected"]
    (output / "sealed").mkdir()
    write_json(output / "sealed/truth.json", truth)
    write_json(
        output / "registration.json",
        {
            "schema": 1,
            "source": str(source),
            "jobs": jobs,
            "baseline": selected,
            "source_registration_sha256": digest(source / "registration.json"),
            "settings_sha256": digest(output / "settings.json"),
            "truth_sha256": digest(output / "sealed/truth.json"),
            "code_sha256": {
                str(Path(__file__).relative_to(ROOT)): digest(__file__),
                str(Path(dsp_inference.__file__).relative_to(ROOT)): digest(dsp_inference.__file__),
            },
            "max_http_attempts": len(jobs) - len(reused),
            "reused_results": reused,
            "spending_cap_usd": None,
            "selection": "First lexical known query in Jin correct; Ottawa correct, wrong class, "
            "false rejection; retain each paired excluded case. "
            "Purposive, previously consumed data.",
            "authorization": "User requests diagram attribution tests and an all-view survey.",
            "stop_rule": "One attempt per job; stop on technical failure; no automatic retries.",
            "limitations": "Self-reported attribution is not causal importance. One reference per "
            "class cannot establish predictive performance. Historical paired comparison is not "
            "randomized and mixes schema, prompt and output-budget changes.",
        },
    )
    return {"surveys": len(surveys), "decisions": len(rows), "jobs": jobs, "baseline": selected}


def verify(output):
    output = Path(output)
    registration = read_json(output / "registration.json")
    for filename, expected in registration["code_sha256"].items():
        if digest(ROOT / filename) != expected:
            raise ValueError("Registered implementation changed.")
    for filename, field in (
        ("settings.json", "settings_sha256"),
        ("sealed/truth.json", "truth_sha256"),
    ):
        if digest(output / filename) != registration[field]:
            raise ValueError("Registered settings or truth changed.")
    for job in registration["jobs"]:
        folder = output / job["name"]
        for filename, field in [
            ("contract.json", "contract_sha256"),
            ("request.json", "request_sha256")
            if job["stage"] == "survey"
            else ("original.json", "original_sha256"),
        ]:
            if digest(folder / filename) != job[field]:
                raise ValueError("Registered input changed.")
    return registration


def completed_result(folder, contract, stage):
    folder = Path(folder)
    receipt = read_json(folder / "attempt.json")
    if (
        receipt["status"] != "completed"
        or digest(folder / "response.json") != receipt["response_sha256"]
        or digest(folder / "request.json") != receipt["request_sha256"]
    ):
        raise ValueError("Completed response binding failed.")
    result = json.loads(read_json(folder / "response.json")["choices"][0]["message"]["content"])
    if result != receipt["result"]:
        raise ValueError("Receipt differs from actual model content.")
    return validate_audit(result, contract, stage)


def execute_one(output, name, client_factory=httpx.Client):
    output = Path(output)
    registration = verify(output)
    matches = [job for job in registration["jobs"] if job["name"] == name]
    if len(matches) != 1:
        raise ValueError("Unregistered job.")
    job = matches[0]
    for other in registration["jobs"]:
        previous = output / other["name"] / "attempt.json"
        if previous.exists() and read_json(previous)["status"] != "completed":
            raise ValueError("An unresolved technical attempt blocks continuation.")
    folder = output / name
    contract = read_json(folder / "contract.json")
    if job["stage"] == "decision":
        survey_folder = output / job["survey"]
        survey = completed_result(
            survey_folder, read_json(survey_folder / "contract.json"), "survey"
        )
        body = decision_body(read_json(folder / "original.json"), contract, survey)
        with (folder / "request.json").open("xb") as stream:
            stream.write(canonical_json(body))
        write_json(
            folder / "request-binding.json",
            {
                "request_sha256": digest(folder / "request.json"),
                "survey_response_sha256": digest(survey_folder / "response.json"),
                "original_sha256": job["original_sha256"],
            },
        )
    settings = read_json(output / "settings.json")
    payload = (folder / "request.json").read_bytes()
    receipt = {
        "status": "reserved",
        "http_attempts": 0,
        "estimated_cost_usd": None,
        "request_sha256": digest(folder / "request.json"),
        "stage": job["stage"],
    }
    with (folder / "attempt.json").open("xb") as stream:
        stream.write(canonical_json(receipt))
    started = time.perf_counter()
    try:
        target = dsp_inference.verify_target(settings)
        if target["sku"]["capacity"] != settings["expected_capacity"]:
            raise ValueError("Deployment capacity changed.")
        receipt["target"] = target
        token = dsp_inference.azure_json(
            [
                "account",
                "get-access-token",
                "--resource",
                "https://ai.azure.com",
                "--subscription",
                settings["subscription"],
            ],
            settings,
        )["accessToken"]
        receipt.update(status="http_started", http_attempts=1)
        write_json(folder / "attempt.json", receipt)
        with client_factory(
            timeout=httpx.Timeout(240, connect=15, write=30, pool=5), follow_redirects=False
        ) as client:
            response = client.post(
                settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                content=payload,
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            )
        del token
        (folder / "response.json").write_bytes(response.content)
        receipt.update(
            http_status=response.status_code,
            response_sha256=digest(folder / "response.json"),
            retry_after=response.headers.get("retry-after"),
        )
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}; raw response retained.")
        envelope = response.json()
        receipt["usage"] = envelope.get("usage")
        try:
            receipt["estimated_cost_usd"] = dsp_inference.estimate_cost(
                envelope.get("usage"), settings
            )
        except ValueError as error:
            receipt["cost_unestablished_reason"] = str(error)
        if envelope.get("model") not in {
            settings["model"],
            settings["model"] + "-" + settings["version"],
        }:
            raise ValueError("Returned model mismatch.")
        choices = envelope.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ValueError("Incomplete completion.")
        message = choices[0]["message"]
        if message.get("refusal"):
            raise ValueError("Model refusal.")
        result = validate_audit(json.loads(message["content"]), contract, job["stage"])
        receipt.update(status="completed", result=result, returned_model=envelope["model"])
    except Exception as error:
        receipt.update(
            status="technical_failure", error_type=type(error).__name__, error=str(error)
        )
    finally:
        receipt["elapsed_seconds"] = time.perf_counter() - started
        write_json(folder / "attempt.json", receipt)
    return {key: value for key, value in receipt.items() if key not in {"result", "target"}}


def evaluate(output):
    output = Path(output)
    registration = verify(output)
    truth = read_json(output / "sealed/truth.json")
    baseline = {row["name"]: row for row in registration["baseline"]}
    rows, surveys, failures = [], [], []
    for job in registration["jobs"]:
        folder = output / job["name"]
        if not (folder / "attempt.json").exists():
            continue
        receipt = read_json(folder / "attempt.json")
        if receipt["status"] != "completed":
            failures.append({"name": job["name"], "receipt": receipt})
            continue
        result = completed_result(folder, read_json(folder / "contract.json"), job["stage"])
        if job["stage"] == "survey":
            surveys.append({"name": job["name"], "dataset": job["dataset"], "result": result})
            continue
        binding = read_json(folder / "request-binding.json")
        if binding["request_sha256"] != receipt["request_sha256"] or binding[
            "survey_response_sha256"
        ] != digest(output / job["survey"] / "response.json"):
            raise ValueError("Survey-to-decision binding changed.")
        decision = result["decision"]
        predicted = decision["condition_id"] if decision["outcome"] == "similar" else "different"
        expected = truth[job["name"]]
        category = (
            ("Correct rejection" if predicted == "different" else "Wrong acceptance")
            if (job["phase"] == "excluded")
            else (
                "Correct class"
                if predicted == expected
                else "False rejection"
                if predicted == "different"
                else "Wrong class"
            )
        )
        rows.append(
            {
                **job,
                "expected": expected,
                "predicted": predicted,
                "category": category,
                "baseline": baseline[job["name"]],
                "result": result,
                "usage": receipt["usage"],
            }
        )
    summary = {
        "registered_decisions": len(truth),
        "completed_decisions": len(rows),
        "completed_surveys": len(surveys),
        "categories": dict(Counter(row["category"] for row in rows)),
        "technical_failures": len(failures),
        "decisive_mentions": dict(
            Counter(key for row in rows for key in row["result"]["decisive_diagrams"])
        ),
        "rows": rows,
        "surveys": surveys,
        "failures": failures,
    }
    write_json(output / "evaluation.json", summary)
    return {
        key: value for key, value in summary.items() if key not in {"rows", "surveys", "failures"}
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Registered all-diagram attribution audit.")
    parser.add_argument("action", choices=("prepare", "one", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("outputs/dsp-extended-ai-v4"))
    parser.add_argument("--resume-source", type=Path)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args.source, args.output, args.resume_source)
    elif args.action == "one":
        result = execute_one(args.output, args.case)
    else:
        result = evaluate(args.output)
    print(json.dumps(result), flush=True)
    if result.get("status") == "technical_failure":
        raise SystemExit(1)
