import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from modelmetis.dsp import DspConfig
from modelmetis.dsp_similarity import (
    invoke_once,
    prepare_comparison,
    render_index,
    verify_bundle,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]


def run_isolated(folder):
    folder = Path(folder)
    verify_bundle(folder)
    settings = json.loads((folder / "settings.json").read_text())
    attempt = folder / "03_response/attempt.json"
    if attempt.exists():
        raise ValueError("Bundle already attempted; automatic retry is forbidden.")
    started = time.perf_counter()
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.compare_dsp",
                "worker",
                "--output",
                str(folder),
            ],
            capture_output=True,
            text=True,
            timeout=settings["request_process_timeout_seconds"],
            check=False,
        )
        if process.returncode and not attempt.exists():
            raise RuntimeError("Worker exited before writing a receipt.")
    except subprocess.TimeoutExpired:
        if attempt.exists():
            (folder / "03_response/interrupted-attempt.json").write_bytes(attempt.read_bytes())
        write_json(
            attempt,
            {
                "status": "technical_failure",
                "error_type": "ProcessDeadline",
                "elapsed_seconds": time.perf_counter() - started,
                "error": "Deadline reached; remote outcome and cost may be unknown.",
            },
        )
        render_index(folder)
    return json.loads(attempt.read_text())


def main():
    parser = argparse.ArgumentParser(description="N complete known WAV reports plus one unknown.")
    parser.add_argument("command", choices=["prepare", "run", "worker"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--settings", type=Path, default=ROOT / "configs/dsp-sol-reuse-v1.json")
    parser.add_argument("--dsp-config", type=Path, default=ROOT / "configs/dsp-report-v1.json")
    args = parser.parse_args()
    if args.command == "prepare":
        if not args.spec:
            parser.error("--spec is required to prepare WAV reports")
        config = DspConfig(**json.loads(args.dsp_config.read_text()))
        result = prepare_comparison(args.spec, args.settings, args.output, config)
        print(
            json.dumps({key: result[key] for key in ("image_count", "request_bytes", "text_bytes")})
        )
    else:
        result = invoke_once(args.output) if args.command == "worker" else run_isolated(args.output)
        print(
            json.dumps(
                {
                    key: result.get(key)
                    for key in ("status", "http_attempts", "elapsed_seconds", "estimated_cost_usd")
                }
            )
        )
        if result["status"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    started = time.perf_counter()
    try:
        main()
    finally:
        print(f"CommandElapsedSeconds={time.perf_counter() - started:.6f}", flush=True)
