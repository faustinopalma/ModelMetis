import argparse
import base64
import html
import json
import time
from dataclasses import asdict
from pathlib import Path

from modelmetis.dsp import DspConfig
from modelmetis.dsp_report import STYLE, THEME, digest, generate_report
from modelmetis.visual_audio import canonical_json

ROOT = Path(__file__).resolve().parents[1]


def run_suite(suite_path, output, config):
    suite_path, output = Path(suite_path), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    (output / "suite-registration.json").write_bytes(canonical_json({
        "suite": suite, "config": asdict(config), "runner_sha256": digest(__file__),
        "selection": "Fixed named inputs; no selection from measured outcomes or diagnoses.",
    }))
    results, sections, table = [], [], []
    for item in suite["recordings"]:
        recording_id = item["recording_id"]
        target = output / recording_id
        case_started = time.perf_counter()
        row = {"dataset": item["dataset"], "recording_id": recording_id,
               "source_state": item["source_state"], "status": "running"}
        try:
            source = suite_path.parent / item["input"]
            result = generate_report(source, target, config, recording_id, item["source_state"])
            manifest = json.loads((target / "manifest.json").read_text())
            row.update(status="completed", duration_seconds=result["duration_seconds"],
                       sample_rate=result["sample_rate"], channels=len(result["channels"]),
                       intervals=result["segment_count"], images=manifest["image_count"],
                       measured_intervals=sum(len(channel["segments"])
                                              for channel in result["channels"]),
                       report_sha256=digest(target / "report.html"),
                       evidence_sha256=digest(target / "evidence.json"),
                       manifest_sha256=digest(target / "manifest.json"),
                       report=f"{recording_id}/report.html")
            first = result["channels"][0]["segments"][0]
            fields = ("rms_db_re_1_fs", "peak_fs", "dc_offset_fs", "clipped_samples")
            row["first_interval"] = {key: first[key] for key in fields}
            row["first_interval"]["fft_peaks_hz"] = [
                peak["frequency_hz"] for peak in first.get("peaks", [])[:3]
            ]
            fft = next((image for image in first["images"]
                        if image["title"] == "FFT amplitude spectrum"), None)
            if fft:
                encoded = base64.b64encode((target / fft["path"]).read_bytes()).decode("ascii")
                sections.append(
                    f'<section><h2><a href="{recording_id}/report.html">'
                    f'{html.escape(item["dataset"])}</a></h2><p>{html.escape(item["source_note"])}'
                    f'</p><figure><a href="{recording_id}/report.html"><img width="1200" '
                    f'height="700" alt="{html.escape(item["dataset"])} FFT preview" '
                    f'src="data:image/png;base64,{encoded}"></a></figure></section>',
                )
            table.append(f'<tr><td><a href="{recording_id}/report.html">'
                         f'{html.escape(item["dataset"])}</a></td>'
                         f'<td>{result["duration_seconds"]:.3f}</td>'
                         f'<td>{result["sample_rate"]:,}</td>'
                         f'<td>{result["segment_count"]}</td>'
                         f'<td>{manifest["image_count"]}</td>'
                         f'<td>{html.escape(item["source_state"])}</td></tr>')
        except Exception as error:
            row.update(status="failed", error_type=type(error).__name__, error=str(error))
            table.append(f'<tr><td>{html.escape(item["dataset"])}</td>'
                         f'<td colspan="5">Failed: {html.escape(str(error))}</td></tr>')
        finally:
            row["elapsed_seconds"] = time.perf_counter() - case_started
            results.append(row)
            with (output / "attempts.jsonl").open("ab") as stream:
                stream.write(canonical_json(row) + b"\n")
            print(json.dumps(row), flush=True)
    summary = {"schema": 1, "kind": "deterministic_dsp_demonstration_not_diagnostic_evaluation",
               "status": "completed" if all(row["status"] == "completed" for row in results)
               and results else "failed", "results": results,
               "elapsed_seconds": time.perf_counter() - started, "llm_calls": 0,
               "protected_C_access": False}
    (output / "summary.json").write_bytes(canonical_json(summary))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>DSP reports | Dataset examples</title>{THEME}<style>{STYLE}</style></head>'
            '<body><header><h1>Audio DSP / Dataset examples</h1>'
            '<p>Analytical reports from four local datasets. No LLM calls, fault labels or '
            'diagnostic conclusions. Original and previously processed recordings are '
            'identified separately; absolute levels are not acquisition-calibrated.</p></header>'
            '<main><div class="table-scroll"><table><thead><tr>'
            '<th>Dataset</th><th>Duration (s)</th>'
            '<th>Sampling (Hz)</th><th>Intervals</th><th>Images</th><th>Source history</th></tr>'
            f'</thead><tbody>{"".join(table)}</tbody></table></div>{"".join(sections)}'
            '</main></body></html>')
    (output / "index.html").write_text(page, encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Deterministic multiview audio DSP reports.")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", type=Path)
    inputs.add_argument("--suite", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/dsp-report-v1.json")
    parser.add_argument("--recording-id", default="R0001")
    parser.add_argument("--source-state", choices=[
        "original", "derived", "derived_peak_normalized", "unknown",
    ], default="unknown")
    args = parser.parse_args()
    config = DspConfig(**json.loads(args.config.read_text(encoding="utf-8")))
    if args.suite:
        result = run_suite(args.suite, args.output, config)
        if result["status"] != "completed":
            raise SystemExit(1)
    else:
        generate_report(args.input, args.output, config, args.recording_id, args.source_state)


if __name__ == "__main__":
    started = time.perf_counter()
    try:
        main()
    finally:
        print(f"CommandElapsedSeconds={time.perf_counter() - started:.6f}", flush=True)