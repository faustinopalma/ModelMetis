import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from modelmetis import dsp_inference, dsp_memory
from modelmetis.dsp_report import digest
from modelmetis.visual_audio import canonical_json
from scripts import dsp_memory_experiment as experiment
from scripts.dsp_extended_experiment import read_json, write_json


def execute_request(directory, settings, client_factory=httpx.Client):
    directory = Path(directory)
    payload = (directory / "request.json").read_bytes()
    contract = read_json(directory / "contract.json")
    if hashlib.sha256(payload).hexdigest() != contract["request_sha256"]:
        raise ValueError("Pending request bytes changed.")
    body = json.loads(payload)
    if (body["model"] != settings["deployment"]
            or body["max_completion_tokens"] != settings["max_completion_tokens"]
            or body["reasoning_effort"] != settings["reasoning_effort"]
            or len(payload) > 64_000_000):
        raise ValueError("Request differs from the registered transport settings.")
    path = directory / "live-attempt.json"
    receipt = {"status": "reserved", "http_attempts": 0, "retries": 0,
               "request_sha256": contract["request_sha256"],
               "contract_sha256": digest(directory / "contract.json"),
               "estimated_cost_usd": None}
    with path.open("xb") as destination:
        destination.write(canonical_json(receipt))
    started = time.perf_counter()
    try:
        receipt["target"] = dsp_inference.verify_target(settings)
        if receipt["target"]["sku"]["capacity"] != settings["expected_capacity"]:
            raise ValueError("Live deployment capacity changed.")
        token = dsp_inference.azure_json([
            "account", "get-access-token", "--resource", "https://ai.azure.com",
            "--subscription", settings["subscription"]], settings)["accessToken"]
        receipt.update(status="http_started", http_attempts=1)
        write_json(path, receipt)
        http_started = time.perf_counter()
        with client_factory(timeout=httpx.Timeout(180, connect=15, write=30, pool=5),
                            follow_redirects=False) as client:
            response = client.post(
                settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                content=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        del token
        receipt["http_seconds"] = time.perf_counter() - http_started
        experiment.put(directory / "live-response.json", response.content)
        receipt.update(http_status=response.status_code,
                       response_sha256=digest(directory / "live-response.json"))
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}; original response retained; no retry.")
        parsed = response.json()
        receipt["usage"] = parsed.get("usage")
        try:
            receipt["estimated_cost_usd"] = dsp_inference.estimate_cost(
                parsed.get("usage"), settings)
        except ValueError as error:
            receipt["cost_unestablished_reason"] = str(error)
        if (parsed.get("model") != experiment.RETURNED_MODEL
                or len(parsed.get("choices", [])) != 1
                or parsed["choices"][0].get("finish_reason") != "stop"
                or parsed["choices"][0]["message"].get("refusal")):
            raise ValueError("Unexpected model identity, refusal or incomplete response.")
        decision = json.loads(parsed["choices"][0]["message"]["content"])
        dsp_memory.validate_decision(decision, contract["evidence_ids"], contract["query_evidence"])
        receipt.update(status="completed", decision=decision, returned_model=parsed["model"])
    except Exception as error:
        receipt.update(status="technical_failure", error_type=type(error).__name__,
                   error=str(error))
    finally:
        receipt["elapsed_seconds"] = time.perf_counter() - started
        receipt["finished_unix"] = time.time()
        write_json(path, receipt)
    return receipt


def register(output, settings_path, previous=None):
    output = Path(output)
    experiment.checked(output)
    for arm in ("fixed", "adaptive"):
        _, split = experiment.checked(output)
        state, _ = experiment.load_state(output, arm, split)
        if state["events"]:
            raise ValueError("Live registration requires unused initial states.")
    settings = read_json(settings_path)
    policy = read_json(output / "policy.json")
    for field in ("deployment", "reasoning_effort", "max_completion_tokens"):
        if settings[field] != policy[field]:
            raise ValueError("Transport differs from the prepared model policy.")
    if settings["model"] + "-" + settings["version"] != experiment.RETURNED_MODEL:
        raise ValueError("Transport model/version differs from the prepared policy.")
    prior, previous_registration = [], None
    prior_http_attempts = 0
    if previous is not None:
        previous = Path(previous)
        previous_registration = digest(previous / "live/registration.json")
        old_registration = read_json(previous / "live/registration.json")
        prior.extend(old_registration.get("prior_attempts", []))
        prior_http_attempts = old_registration.get("prior_http_attempts", 0)
        for path in sorted(previous.glob("requests/*/*/live-attempt.json")):
            receipt = read_json(path)
            prior.append({"path": str(path.resolve()), "sha256": digest(path),
                          "http_attempts": receipt["http_attempts"],
                          "estimated_cost_usd": receipt.get("estimated_cost_usd")})
            prior_http_attempts += receipt["http_attempts"]
        for arm in ("fixed", "adaptive"):
            states = sorted((previous / "states" / arm).glob("*.json"))
            if len(states) != 1 or read_json(states[0])["state"]["events"]:
                raise ValueError("Recovery cannot discard an already advanced stream.")
    if prior_http_attempts >= 288:
        raise ValueError("Combined HTTP attempt budget is exhausted.")
    settings.update(max_real_requests=288, run_deadline_seconds=14400)
    directory = output / "live"
    directory.mkdir(parents=True, exist_ok=False)
    experiment.put(directory / "settings.json", settings)
    experiment.put(directory / "registration.json", {
        "authorization": "User explicitly requested the Ottawa inference tests.",
        "spending_cap_usd": None, "max_http_attempts": 288 - prior_http_attempts,
        "prior_http_attempts": prior_http_attempts, "prior_attempts": prior,
        "previous_live_registration_sha256": previous_registration,
        "minimum_interval_seconds": 25,
        "schedule": "Lowest stream position, summary before retrieval, alternating first arm.",
        "stop_rule": "Stop on technical failure; retain original bytes; no automatic retries.",
        "prepared_registration_sha256": digest(output / "registration.json"),
        "settings_sha256": digest(directory / "settings.json"),
        "code": {Path(__file__).relative_to(experiment.ROOT).as_posix(): digest(__file__),
                 "src/modelmetis/dsp_inference.py": digest(dsp_inference.__file__)},
    })
    return {"status": "registered", "max_http_attempts": 288 - prior_http_attempts,
            "prior_http_attempts": prior_http_attempts, "new_model_calls": 0}


def verify_live(output):
    registration = read_json(output / "live/registration.json")
    if (digest(output / "registration.json") != registration["prepared_registration_sha256"]
            or digest(output / "live/settings.json") != registration["settings_sha256"]):
        raise ValueError("Live registration inputs changed.")
    for name, expected in registration["code"].items():
        if digest(experiment.ROOT / name) != expected:
            raise ValueError("Live transport implementation changed.")
    for attempt in registration["prior_attempts"]:
        if digest(attempt["path"]) != attempt["sha256"]:
            raise ValueError("Preserved prior attempt changed.")
    return registration, read_json(output / "live/settings.json")


def verified_attempt(directory):
    receipt = read_json(directory / "live-attempt.json")
    if receipt["status"] != "completed":
        raise ValueError("An unresolved technical attempt blocks continuation; no retry.")
    for filename, field in (("request.json", "request_sha256"),
                            ("contract.json", "contract_sha256"),
                            ("live-response.json", "response_sha256")):
        if digest(directory / filename) != receipt[field]:
            raise ValueError("Live request, response or contract binding changed.")
    if receipt.get("source_attempt"):
        if digest(receipt["source_attempt"]) != receipt["source_attempt_sha256"]:
            raise ValueError("Reused original attempt changed.")
    return receipt


def adopt(output, arm, source):
    output, source = Path(output), Path(source)
    registration, _ = verify_live(output)
    source_attempt = source / "live-attempt.json"
    if not any(Path(item["path"]).resolve() == source_attempt.resolve()
               for item in registration["prior_attempts"]):
        raise ValueError("Only a registered preserved attempt may be reused.")
    directory = experiment.next_request(output, arm)
    if (directory / "live-attempt.json").exists() or (output / "live/run.lock").exists():
        raise ValueError("The pending request is already reserved.")
    old = read_json(source_attempt)
    contract = read_json(directory / "contract.json")
    if (old.get("http_status") != 200
            or digest(source / "request.json") != contract["request_sha256"]
            or old["request_sha256"] != contract["request_sha256"]
            or digest(source / "live-response.json") != old["response_sha256"]):
        raise ValueError("Reused response requires identical original request bytes.")
    parsed = read_json(source / "live-response.json")
    if (parsed.get("model") != experiment.RETURNED_MODEL
            or len(parsed.get("choices", [])) != 1
            or parsed["choices"][0].get("finish_reason") != "stop"
            or parsed["choices"][0]["message"].get("refusal")):
        raise ValueError("Original completion is not eligible for validation recovery.")
    decision = json.loads(parsed["choices"][0]["message"]["content"])
    dsp_memory.validate_decision(decision, contract["evidence_ids"], contract["query_evidence"])
    receipt = {key: value for key, value in old.items() if key not in {"error", "error_type"}}
    receipt.update(status="completed", decision=decision, returned_model=parsed["model"],
                   http_attempts=0, reused_response=True,
                   source_attempt=str(source_attempt.resolve()),
                   source_attempt_sha256=digest(source_attempt),
                   contract_sha256=digest(directory / "contract.json"),
                   recovery="Original accepted response revalidated; no new HTTP or text repair.")
    experiment.put(directory / "live-response.json", (source / "live-response.json").read_bytes())
    experiment.put(directory / "live-attempt.json", receipt)
    verified_attempt(directory)
    experiment.submit(output, arm, directory / "live-response.json")
    return {"status": "reused_original_response", "new_http_attempts": 0,
            "request_sha256": contract["request_sha256"]}


def run(output, limit):
    output = Path(output)
    if not 1 <= limit <= 288:
        raise ValueError("Batch limit must be within the registered stream budget.")
    registration, settings = verify_live(output)
    _, split = experiment.checked(output)
    lock = output / "live/run.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    started, new_attempts = time.monotonic(), 0
    try:
        while new_attempts < limit:
            verify_live(output)
            experiment.checked(output)
            attempts = list(output.glob("requests/*/*/live-attempt.json"))
            receipts = [verified_attempt(path.parent) for path in attempts]
            states = {arm: experiment.load_state(output, arm, split)[0]
                      for arm in ("fixed", "adaptive")}
            active = [arm for arm, state in states.items()
                      if state["position"] < len(split["stream"])]
            if not active:
                break
            priority = {"summary": 0, "retrieval": 1, "human": 2}
            arm = min(active, key=lambda name: (
                states[name]["position"], priority[states[name]["stage"]],
                int(name != ("fixed" if states[name]["position"] % 2 == 0 else "adaptive"))))
            state = states[arm]
            if state["stage"] == "human":
                reviewed = experiment.review(output, arm)
                print(json.dumps({"arm": arm, "event": "human_review", **reviewed}), flush=True)
                continue
            directory = experiment.next_request(output, arm)
            if not (directory / "live-attempt.json").exists():
                if sum(receipt["http_attempts"] for receipt in receipts) >= (
                    registration["max_http_attempts"]
                ):
                    raise ValueError("Registered HTTP attempt budget exhausted.")
                if time.monotonic() - started >= settings["run_deadline_seconds"]:
                    raise ValueError("Run deadline reached; checkpoints retained.")
                latest = max((receipt["finished_unix"] for receipt in receipts), default=0)
                delay = latest + registration["minimum_interval_seconds"] - time.time()
                if delay > 0:
                    print(json.dumps({"event": "quota_pacing", "seconds": round(delay, 1)}),
                          flush=True)
                    time.sleep(delay)
                result = execute_request(directory, settings)
                new_attempts += 1
                print(json.dumps({"arm": arm, "position": state["position"],
                                  "stage": state["stage"], "status": result["status"],
                                  "decision": result.get("decision", {}).get("decision"),
                                  "cost_usd": result.get("estimated_cost_usd")}), flush=True)
                if result["status"] != "completed":
                    raise RuntimeError("Technical inference failure retained; campaign stopped.")
            verified_attempt(directory)
            experiment.submit(output, arm, directory / "live-response.json")
        return {"new_http_attempts": new_attempts, **experiment.status(output)}
    finally:
        lock.unlink()


def evaluate(output):
    output = Path(output)
    registration, _ = verify_live(output)
    results = experiment.evaluate_stream(output)
    _, split = experiment.checked(output)
    rows = []
    for arm in ("fixed", "adaptive"):
        state, _ = experiment.load_state(output, arm, split)
        for event in state["events"]:
            if event["kind"] != "decision":
                continue
            position = split["stream"].index(event["query_id"])
            directory = output / "requests" / arm / f"{position:03d}-{event['stage']}"
            receipt = verified_attempt(directory)
            if (receipt["request_sha256"] != event["request_sha256"]
                    or receipt["response_sha256"] != event["response_sha256"]
                    or receipt["decision"] != event["decision"]):
                raise ValueError("Scored decision differs from the measured response.")
            rows.append({"arm": arm, "query_id": event["query_id"], "stage": event["stage"],
                         **receipt})
    count = len(list(output.glob("requests/*/*/live-attempt.json")))
    if count != len(rows):
        raise ValueError("Some live attempts are not accounted for in scored decisions.")
    billed = [row for row in rows if row["http_attempts"]]
    priced = [row["estimated_cost_usd"] for row in billed
              if row["estimated_cost_usd"] is not None]
    report = {"arms": results["arms"], "http_attempts": len(billed),
              "reused_decisions": count - len(billed), "model_decisions": count,
              "prompt_tokens": sum(row["usage"]["prompt_tokens"] for row in billed),
              "completion_tokens": sum(row["usage"]["completion_tokens"] for row in billed),
              "priced_attempts": len(priced), "unpriced_attempts": len(billed) - len(priced),
              "estimated_cost_usd": sum(priced), "cost_complete": len(priced) == len(billed),
              "prior_http_attempts": registration["prior_http_attempts"],
              "combined_http_attempts": len(billed) + registration["prior_http_attempts"],
              "prior_estimated_cost_usd": sum(item["estimated_cost_usd"] or 0
                                              for item in registration["prior_attempts"]),
              "scope": "Measured development stream; transport hashes verified.",
              "reserved_evaluation": "locked_not_executed"}
    experiment.put(output / "live/results.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run registered Ottawa model inference once.")
    parser.add_argument("action", choices=["register", "run", "evaluate", "adopt"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--source-request", type=Path)
    parser.add_argument("--arm", choices=["fixed", "adaptive"], default="fixed")
    parser.add_argument("--limit", type=int, default=288)
    args = parser.parse_args()
    if args.action == "register":
        if args.settings is None:
            parser.error("register requires --settings")
        result = register(args.output, args.settings, args.previous)
    elif args.action == "run":
        result = run(args.output, args.limit)
    elif args.action == "adopt":
        if args.source_request is None:
            parser.error("adopt requires --source-request")
        result = adopt(args.output, args.arm, args.source_request)
    else:
        result = evaluate(args.output)
    print(json.dumps(result, indent=2))