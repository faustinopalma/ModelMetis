import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from modelmetis.dsp_packet import digest, validate_decision
from modelmetis.visual_audio import canonical_json


def azure_json(arguments, settings):
    executable = shutil.which("az")
    if executable is None:
        raise RuntimeError("Azure CLI is not installed.")
    environment = {
        **os.environ, "AZURE_CONFIG_DIR": str(Path(settings["azure_config_dir"]).resolve()),
    }
    result = subprocess.run([executable, *arguments, "-o", "json"], capture_output=True,
                            text=True, encoding="utf-8", env=environment, timeout=25, check=False)
    if result.returncode:
        raise RuntimeError(f"Azure CLI {arguments[0]} operation failed, exit {result.returncode}.")
    return json.loads(result.stdout)


def verify_target(settings):
    parsed = urlparse(settings["endpoint"])
    if (parsed.scheme != "https" or parsed.hostname != f"{settings['account']}.openai.azure.com"
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.port is not None or parsed.path not in ("", "/")):
        raise ValueError("Inference endpoint does not match the declared Azure resource.")
    account = azure_json(["account", "show", "--subscription", settings["subscription"]], settings)
    if account["id"] != settings["subscription"] or account["tenantId"] != settings["tenant"]:
        raise ValueError("Azure subscription or tenant mismatch.")
    deployment = azure_json([
        "cognitiveservices", "account", "deployment", "show", "--name", settings["account"],
        "--resource-group", settings["resource_group"], "--deployment-name", settings["deployment"],
        "--subscription", settings["subscription"],
    ], settings)
    properties = deployment["properties"]
    model = properties["model"]
    if (properties["provisioningState"] != "Succeeded" or model["name"] != settings["model"]
            or model["version"] != settings["version"] or model["format"] != "OpenAI"
            or properties["versionUpgradeOption"] != "NoAutoUpgrade"
            or deployment["sku"]["name"] != settings["sku"]):
        raise ValueError("Live deployment differs from the frozen model/version/SKU.")
    return {"id": deployment["id"], "model": model, "sku": deployment["sku"],
            "upgrade": properties["versionUpgradeOption"], "state": properties["provisioningState"]}


def estimate_cost(usage, settings):
    if not isinstance(usage, dict):
        raise ValueError("Missing token usage; cost cannot be established.")
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    if (any(type(value) is not int or value < 0 for value in (prompt, completion, cached))
            or cached > prompt or prompt > 64000 or completion > settings["max_completion_tokens"]):
        raise ValueError("Token accounting is outside the registered short-context bounds.")
    rates = settings["prices_usd_per_million"]
    return ((prompt - cached) * rates["input"] + cached * rates["cached_input"]
            + completion * rates["output"]) / 1_000_000


def parse_completion(response, job, settings):
    allowed_models = {settings["model"], f"{settings['model']}-{settings['version']}"}
    if response.get("model") not in allowed_models:
        raise ValueError("Returned model identity differs from the verified deployment.")
    choices = response.get("choices", [])
    if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
        raise ValueError("Completion missing, truncated, filtered or otherwise incomplete.")
    message = choices[0]["message"]
    if message.get("refusal") or not isinstance(message.get("content"), str):
        raise ValueError("Model refusal or missing structured content.")
    decision = validate_decision(
        json.loads(message["content"]), job["allowed_ids"], job["evidence_ids"],
    )
    cost = estimate_cost(response.get("usage"), settings)
    return {"decision": decision, "usage": response["usage"], "estimated_cost_usd": cost,
            "returned_model": response["model"], "response_id": response.get("id")}


def execute_one(job_path, settings_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    attempt = {"status": "reserved", "http_attempts": 0, "retries": 0,
               "request_file_sha256": digest(Path(job_path).read_bytes()),
               "estimated_cost_usd": None}
    (output / "attempt.json").write_bytes(canonical_json(attempt))
    try:
        settings = json.loads(Path(settings_path).read_text(encoding="utf-8"))
        job = json.loads(Path(job_path).read_text(encoding="utf-8"))
        body = job["body"]
        if (digest(canonical_json(body)) != job["body_sha256"]
                or body["model"] != settings["deployment"]
                or body["max_completion_tokens"] != settings["max_completion_tokens"]
                or body["reasoning_effort"] != settings["reasoning_effort"]
                or len(canonical_json(body)) > 5_000_000):
            raise ValueError("Request differs from its immutable inference contract.")
        attempt["target"] = verify_target(settings)
        token_result = azure_json([
            "account", "get-access-token", "--resource", "https://ai.azure.com",
            "--subscription", settings["subscription"],
        ], settings)
        token = token_result["accessToken"]
        del token_result
        (output / "request.json").write_bytes(canonical_json(body))
        attempt.update(status="http_started", http_attempts=1)
        (output / "attempt.json").write_bytes(canonical_json(attempt))
        http_started = time.perf_counter()
        with httpx.Client(timeout=httpx.Timeout(120, connect=15, write=30, pool=5),
                          follow_redirects=False) as client:
            response = client.post(settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                                   headers={"Authorization": f"Bearer {token}"}, json=body)
        del token
        attempt["model_http_seconds"] = time.perf_counter() - http_started
        attempt["http_status"] = response.status_code
        (output / "response.json").write_bytes(response.content)
        if response.status_code != 200:
            raise RuntimeError(f"Model HTTP {response.status_code}; response retained; no retry.")
        parsed = response.json()
        if isinstance(parsed.get("usage"), dict):
            attempt["usage"] = parsed["usage"]
            attempt["estimated_cost_usd"] = estimate_cost(parsed["usage"], settings)
        attempt.update(parse_completion(parsed, job, settings), status="completed")
    except Exception as error:
        attempt.update(status="failed", error_type=type(error).__name__, error=str(error))
    finally:
        attempt["elapsed_seconds"] = time.perf_counter() - started
        (output / "attempt.json").write_bytes(canonical_json(attempt))
    return attempt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One immutable Azure DSP comparison; no retries.")
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute_one(args.job, args.settings, args.output)
    print(json.dumps({key: result[key] for key in ("status", "http_attempts", "elapsed_seconds")}))
    raise SystemExit(0 if result["status"] == "completed" else 1)