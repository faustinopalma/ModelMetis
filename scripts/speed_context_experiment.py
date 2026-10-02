"""MAFAULDA model test: reports only, reports plus speed context, reports plus healthy differences.

prepare  selects cases with a fixed seed, writes WAVs, DSP reports and the exact requests.
run      sends every prepared request once; HTTP 429 waits and repeats the identical bytes.
evaluate scores decisions against folder labels beside the deterministic numerical controls.
"""

import argparse
import base64
import io
import json
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import httpx
import matplotlib
import numpy as np
import soundfile as sf
from PIL import Image

from modelmetis import dsp_inference
from modelmetis.dsp import DspConfig
from modelmetis.dsp_packet import digest
from modelmetis.dsp_report import generate_report
from modelmetis.dsp_similarity import (
    PROMPT,
    contact_sheet,
    decision_schema,
    file_hash,
    full_report,
    messages_for,
    validate_result,
    write_json,
)
from modelmetis.visual_audio import canonical_json
from scripts import difference_screen as screen

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
RATE = 50000
SEED = 20261001
RATIOS = (1.0, 1.1, 1.3, 2.0)
PER_CLASS = 2
ARMS = ("reports", "speed", "difference")
LABELS = {
    "normal": "normal (healthy machine)",
    "imbalance": "rotor imbalance",
    "horizontal-misalignment": "horizontal shaft misalignment",
    "vertical-misalignment": "vertical shaft misalignment",
    "underhang-ball_fault": "ball defect, bearing between rotor and motor",
    "underhang-cage_fault": "cage defect, bearing between rotor and motor",
    "underhang-outer_race": "outer-race defect, bearing between rotor and motor",
    "overhang-ball_fault": "ball defect, outer bearing",
    "overhang-cage_fault": "cage defect, outer bearing",
    "overhang-outer_race": "outer-race defect, outer bearing",
}
CLASSES = tuple(LABELS)
SPEED_GUIDANCE = (
    "Operating context: the supplied context states the shaft rotation frequency of every "
    "report, and speeds differ between reports. Components locked to rotation, such as shaft "
    "harmonics, imbalance, misalignment and bearing defect frequencies, scale in proportion to "
    "shaft speed: compare them in orders, frequency divided by shaft frequency, using each "
    "report's order-axis figure. Components fixed in hertz, such as structural resonances, "
    "electrical lines and the microphone response, stay at the same frequency when speed "
    "changes. Overall level and broadband shape can also change with speed."
)
DIFFERENCE_GUIDANCE = (
    "Each report also has a difference figure: its Welch spectrum minus the Welch spectrum of "
    "the healthy machine recorded at the same speed as that report. The difference shows what "
    "the condition adds to or removes from the healthy machine. The healthy reference's "
    "difference is zero by definition. Compare the unknown report's difference with each "
    "reference's difference, together with the full reports."
)
SETTINGS_BASE = "configs/dsp-sol-reuse-v1.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mafaulda_inventory(cache, audit):
    index = read_json(Path(cache) / "index.json")
    records = {row["member"]: row for row in read_json(audit)}
    speeds = sorted(float(m.split("/")[-1][:-4]) for m in index if m.startswith("normal/"))
    items = {}
    for member, name in index.items():
        if records[member]["microphone"]["peak"] > 5:
            continue
        nominal = float(member.split("/")[-1][:-4])
        measured = records[member]["rotation_hz"]
        shaft = measured if measured and abs(measured / nominal - 0.977) < 0.03 else 0.977 * nominal
        items[member] = {"member": member, "class": screen.mafaulda_class(member),
                         "speed_index": int(np.argmin([abs(nominal - v) for v in speeds])),
                         "shaft_hz": shaft, "cache": str(Path(cache) / name)}
    return items, speeds


def select_cases(items, speeds):
    cells = defaultdict(list)
    for member, item in items.items():
        cells[(item["class"], item["speed_index"])].append(member)
    normals = {item["speed_index"]: m for m, item in items.items() if item["class"] == "normal"}
    rng = np.random.default_rng(SEED)
    cases = []
    for ratio in RATIOS:
        eligible = defaultdict(list)
        for member, item in sorted(items.items()):
            if item["class"] == "normal":
                continue
            target = speeds[item["speed_index"]] * ratio
            ref_index = int(np.argmin([abs(target - v) for v in speeds]))
            if abs(speeds[ref_index] / target - 1) > 0.03 or ref_index not in normals:
                continue
            references = {}
            for label in CLASSES:
                pool = sorted(m for m in cells.get((label, ref_index), []) if m != member)
                if pool:
                    references[label] = pool[len(pool) // 2]
            if len(references) == len(CLASSES):
                eligible[item["class"]].append({
                    "query": member, "ratio": ratio, "references": references,
                    "query_normal": normals[item["speed_index"]], "reference_normal":
                    normals[ref_index]})
        for label in CLASSES[1:]:
            pool = eligible[label]
            if len(pool) < PER_CLASS:
                raise ValueError(f"Too few eligible {label} queries at ratio {ratio}.")
            for position in sorted(rng.choice(len(pool), PER_CLASS, replace=False).tolist()):
                cases.append(pool[position])
    for number, case in enumerate(cases, 1):
        case["id"] = f"M{number:03d}"
    return cases


def write_wav(item, folder):
    path = folder / "wav" / (item["member"].replace("/", "__")[:-4] + ".wav")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, np.load(item["cache"]), RATE, subtype="FLOAT")
    return path


def png(figure):
    import matplotlib.pyplot as plt

    stream = io.BytesIO()
    figure.savefig(stream, format="png", dpi=100)
    plt.close(figure)
    with Image.open(io.BytesIO(stream.getvalue())) as image:
        clean = io.BytesIO()
        image.convert("RGB").save(clean, format="PNG")
    return clean.getvalue()


def order_figure(samples, shaft_hz):
    import matplotlib.pyplot as plt

    frequencies, level = screen.welch_db(samples, RATE, screen.FINE)
    orders = frequencies / shaft_hz
    figure, axes = plt.subplots(2, 1, figsize=(12, 7))
    near = orders <= 20
    axes[0].plot(orders[near], level[near], lw=0.8, color="#0078d4")
    axes[0].set(xlim=(0, 20), xlabel="Order (frequency / shaft frequency)", ylabel="dB",
                title=f"Welch spectrum on an order axis, shaft {shaft_hz:.3f} Hz")
    axes[0].set_xticks(range(0, 21))
    axes[0].grid(alpha=0.3)
    wide = (orders >= 0.5) & (orders <= 300)
    axes[1].semilogx(orders[wide], level[wide], lw=0.6, color="#0078d4")
    axes[1].set(xlim=(0.5, 300), xlabel="Order, logarithmic", ylabel="dB")
    axes[1].grid(alpha=0.3, which="both")
    figure.tight_layout()
    return png(figure)


def difference_figure(samples, normal_samples, is_normal):
    import matplotlib.pyplot as plt

    frequencies, level = screen.welch_db(samples, RATE, screen.COARSE)
    _, base = screen.welch_db(normal_samples, RATE, screen.COARSE)
    delta = np.zeros_like(level) if is_normal else level - base
    figure, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].semilogx(frequencies, delta, lw=0.8, color="#b11f4b")
    axes[0].axhline(0, color="black", lw=0.6)
    axes[0].set(xlim=(20, 20000), xlabel="Frequency (Hz), logarithmic", ylabel="dB",
                title="Difference from the healthy machine at the same speed")
    axes[0].grid(alpha=0.3, which="both")
    fine_f, fine = screen.welch_db(samples, RATE, 8192)
    _, fine_base = screen.welch_db(normal_samples, RATE, 8192)
    fine_delta = np.zeros_like(fine) if is_normal else fine - fine_base
    low = fine_f <= 1000
    axes[1].plot(fine_f[low], fine_delta[low], lw=0.8, color="#b11f4b")
    axes[1].axhline(0, color="black", lw=0.6)
    axes[1].set(xlim=(0, 1000), xlabel="Frequency (Hz), 8,192-sample frames", ylabel="dB")
    axes[1].grid(alpha=0.3)
    figure.tight_layout()
    return png(figure)


def extra_part(report, payload, suffix, title):
    identifier = f"{report['model']['id']}.{suffix}"
    report["evidence_ids"].append(identifier)
    return {"id": identifier, "title": title, "bytes": payload, "sha256": digest(payload)}


def build_request(case, arm, items, folder, settings, config):
    def report_for(member, identifier):
        source = write_wav(items[member], folder)
        target = folder / "reports" / member.replace("/", "__")[:-4]
        if not target.exists():
            generate_report(source, target, config, "R0001", "derived")
        packed = contact_sheet(full_report(target, identifier))
        if packed["audit"]["source_sha256"] != file_hash(source):
            raise ValueError("Report belongs to another WAV.")
        return packed

    members = {f"C{i:02d}": case["references"][label] for i, label in enumerate(CLASSES, 1)}
    known = {cid: report_for(member, f"R{i:02d}") for i, (cid, member) in
             enumerate(members.items(), 1)}
    unknown = report_for(case["query"], "Q01")
    labels = {f"C{i:02d}": LABELS[label] for i, label in enumerate(CLASSES, 1)}
    messages = messages_for(known, unknown, image_detail="high", condition_labels=labels)
    extras, context = [], {}
    signals = {cid: (members[cid], case["reference_normal"]) for cid in members}
    signals["Q01"] = (case["query"], case["query_normal"])
    reports = {**{cid: known[cid] for cid in members}, "Q01": unknown}
    if arm == "speed":
        messages[0]["content"] += " " + SPEED_GUIDANCE
        speeds = {}
        for cid, (member, _) in signals.items():
            shaft = items[member]["shaft_hz"]
            speeds[reports[cid]["model"]["id"]] = {"shaft_hz": round(shaft, 3),
                                                   "rpm": round(60 * shaft, 1)}
            extras.append(extra_part(reports[cid], order_figure(np.load(items[member]["cache"]),
                                                                 shaft),
                                     "O001", "Welch spectrum on an order axis"))
        context = {"operating_context": speeds, "order_figures": [e["id"] for e in extras]}
    elif arm == "difference":
        messages[0]["content"] += " " + DIFFERENCE_GUIDANCE
        for cid, (member, normal) in signals.items():
            payload = difference_figure(np.load(items[member]["cache"]),
                                        np.load(items[normal]["cache"]),
                                        items[member]["class"] == "normal")
            extras.append(extra_part(reports[cid], payload, "D001",
                                     "Difference from the healthy machine at the same speed"))
        context = {"difference_figures": [e["id"] for e in extras],
                   "difference_definition": "Welch dB of the report minus Welch dB of the "
                   "healthy recording at the report's own speed; 1,024-sample frames for "
                   "20 Hz-20 kHz and 8,192-sample frames for 0-1,000 Hz"}
    if extras:
        content = messages[1]["content"]
        content.append({"type": "text", "text": canonical_json(context).decode()})
        for extra in extras:
            content.extend([
                {"type": "text", "text": f"{extra['id']}: {extra['title']}"},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64," + base64.b64encode(extra["bytes"]).decode(),
                    "detail": "high"}}])
    body = {"model": settings["deployment"], "messages": messages,
            "reasoning_effort": settings["reasoning_effort"],
            "max_completion_tokens": settings["max_completion_tokens"],
            "response_format": decision_schema(list(known))}
    evidence = {"known": {cid: report["evidence_ids"] for cid, report in known.items()},
                "unknown": unknown["evidence_ids"]}
    return body, evidence


def prepare(folder, cache, audit):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    settings = read_json(ROOT / SETTINGS_BASE)
    settings.update(max_completion_tokens=8192, image_detail="high",
                    prices_usd_per_million={"input": 4.4, "cached_input": 0.44, "output": 22.0})
    write_json(folder / "settings.json", settings)
    config = replace(DspConfig(), segment_seconds=5.0, max_plot_segments=1)
    write_json(folder / "dsp-config.json", asdict(config))
    items, speeds = mafaulda_inventory(cache, audit)
    cases = select_cases(items, speeds)
    write_json(folder / "cases.json", cases)
    write_json(folder / "registration.json", {
        "arms": ARMS, "ratios": RATIOS, "per_class": PER_CLASS, "seed": SEED,
        "cases": len(cases), "requests": len(cases) * len(ARMS),
        "cases_sha256": file_hash(folder / "cases.json"),
        "settings_sha256": file_hash(folder / "settings.json"),
        "code_sha256": {"experiment": file_hash(__file__), "screen": file_hash(screen.__file__)},
        "prompt_base_sha256": digest(PROMPT.encode()),
        "scope": "MAFAULDA microphone, one rig, publisher folder labels; spike files excluded",
    })
    for case in cases:
        for arm in ARMS:
            target = folder / "requests" / arm / case["id"]
            target.mkdir(parents=True)
            body, evidence = build_request(case, arm, items, folder, settings, config)
            payload = canonical_json(body)
            (target / "request.json").write_bytes(payload)
            write_json(target / "evidence.json", evidence)
            write_json(target / "binding.json", {"request_sha256": digest(payload),
                                                 "bytes": len(payload)})
        print(case["id"], case["ratio"], case["query"], flush=True)
    return len(cases)


def price(usage, settings):
    rates = settings["prices_usd_per_million"]
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return ((usage["prompt_tokens"] - cached) * rates["input"] + cached * rates["cached_input"]
            + usage["completion_tokens"] * rates["output"]) / 1_000_000


class Token:
    def __init__(self, settings):
        self.settings, self.value, self.time, self.lock = settings, None, 0.0, threading.Lock()

    def get(self):
        with self.lock:
            if time.time() - self.time > 1500:
                self.value = dsp_inference.azure_json(
                    ["account", "get-access-token", "--resource", "https://ai.azure.com",
                     "--subscription", self.settings["subscription"]], self.settings)["accessToken"]
                self.time = time.time()
            return self.value


def send(target, settings, token):
    binding = read_json(target / "binding.json")
    payload = (target / "request.json").read_bytes()
    if digest(payload) != binding["request_sha256"]:
        raise ValueError("Request changed after preparation.")
    attempt = {"status": "started", "http_attempts": 0, "rate_limited": 0}
    started = time.perf_counter()
    while True:
        attempt["http_attempts"] += 1
        with httpx.Client(timeout=httpx.Timeout(300, connect=15, write=60, pool=5)) as client:
            response = client.post(
                settings["endpoint"].rstrip("/") + "/openai/v1/chat/completions",
                content=payload, headers={"Authorization": f"Bearer {token.get()}",
                                          "Content-Type": "application/json"})
        if response.status_code == 429 and attempt["rate_limited"] < 20:
            attempt["rate_limited"] += 1
            time.sleep(float(response.headers.get("retry-after", 30)) + 2)
            continue
        break
    attempt.update(http_status=response.status_code, seconds=time.perf_counter() - started)
    (target / "response.json").write_bytes(response.content)
    try:
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        result = response.json()
        attempt["usage"] = result.get("usage")
        attempt["estimated_cost_usd"] = price(result["usage"], settings)
        if result.get("model") not in {settings["model"],
                                       f"{settings['model']}-{settings['version']}"}:
            raise ValueError("Unexpected model identity.")
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError(f"Finish reason {choice.get('finish_reason')}.")
        evidence = read_json(target / "evidence.json")
        decision = validate_result(json.loads(choice["message"]["content"]),
                                   evidence["known"], evidence["unknown"])
        write_json(target / "decision.json", decision)
        attempt.update(status="completed", outcome=decision["outcome"],
                       condition_id=decision["condition_id"])
    except Exception as error:
        attempt.update(status="failed", error_type=type(error).__name__, error=str(error))
    write_json(target / "attempt.json", attempt)
    return attempt


def run(folder, workers, arms):
    folder = Path(folder)
    settings = read_json(folder / "settings.json")
    registration = read_json(folder / "registration.json")
    if registration["settings_sha256"] != file_hash(folder / "settings.json"):
        raise ValueError("Settings changed after registration.")
    dsp_inference.verify_target(settings)
    token = Token(settings)
    token.get()
    pending = [path for arm in arms for path in sorted((folder / "requests" / arm).iterdir())
               if not (path / "attempt.json").exists()]
    pending.sort(key=lambda path: (path.name, path.parent.name))
    with ThreadPoolExecutor(workers) as pool:
        futures = [(target, pool.submit(send, target, settings, token)) for target in pending]
        for target, future in futures:
            attempt = future.result()
            print(target.parent.name, target.name, attempt["status"],
                  attempt.get("condition_id"), round(attempt.get("estimated_cost_usd") or 0, 4),
                  flush=True)


def evaluate(folder):
    folder = Path(folder)
    cases = {case["id"]: case for case in read_json(folder / "cases.json")}
    items, _ = mafaulda_inventory(*read_json(folder / "sources.json"))
    loaded = {}

    def load(member):
        if member not in loaded:
            loaded[member] = screen.features(np.load(items[member]["cache"]), RATE,
                                             items[member]["shaft_hz"])
        return loaded[member]

    rows, cost, tokens = [], 0.0, Counter()
    for case_id, case in cases.items():
        expected = f"C{CLASSES.index(screen.mafaulda_class(case['query'])) + 1:02d}"
        query = screen.vectors(load(case["query"]), load(case["query_normal"]))
        references = {}
        for i, label in enumerate(CLASSES, 1):
            member = case["references"][label]
            if label == "normal":
                base = screen.vectors(load(member), None)
                base.update(screen.zero_delta(load(member)))
            else:
                base = screen.vectors(load(member), load(case["reference_normal"]))
            references[f"C{i:02d}"] = [base]
        for method in ("raw", "order", "delta"):
            ranked, _ = screen.decide(query, references, method)
            rows.append({"case": case_id, "ratio": case["ratio"], "arm": f"numeric-{method}",
                         "expected": expected, "predicted": ranked[0], "status": "completed"})
        for arm in ARMS:
            path = folder / "requests" / arm / case_id / "attempt.json"
            attempt = read_json(path) if path.exists() else {"status": "missing"}
            cost += attempt.get("estimated_cost_usd") or 0
            for key, value in (attempt.get("usage") or {}).items():
                if isinstance(value, int):
                    tokens[key] += value
            predicted = (attempt.get("condition_id") or "different"
                         if attempt["status"] == "completed" else None)
            rows.append({"case": case_id, "ratio": case["ratio"], "arm": arm,
                         "expected": expected, "predicted": predicted,
                         "status": attempt["status"]})
    table = defaultdict(Counter)
    for row in rows:
        cell = table[(row["arm"], row["ratio"])]
        cell["total"] += 1
        if row["status"] != "completed":
            cell["technical_failure"] += 1
        elif row["predicted"] == row["expected"]:
            cell["correct"] += 1
        elif row["predicted"] == "different":
            cell["different"] += 1
        else:
            cell["wrong"] += 1
    summary = [{"arm": arm, "ratio": ratio, **dict(cell)}
               for (arm, ratio), cell in sorted(table.items())]
    write_json(folder / "evaluation.json", {"summary": summary, "rows": rows,
                                            "estimated_cost_usd": cost, "tokens": dict(tokens)})
    return summary, cost, dict(tokens)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["prepare", "run", "evaluate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("data/derived/mafaulda-microphone"))
    parser.add_argument("--audit", type=Path, default=Path("outputs/mafaulda-audit-v1/files.json"))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--arms", nargs="+", default=list(ARMS))
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.output, args.cache, args.audit))
        write_json(args.output / "sources.json", [str(args.cache), str(args.audit)])
    elif args.command == "run":
        run(args.output, args.workers, args.arms)
    else:
        summary, cost, tokens = evaluate(args.output)
        for row in summary:
            print(row)
        print("estimated cost USD", round(cost, 4), tokens)
