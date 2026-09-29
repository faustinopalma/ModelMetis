import argparse
import html
import json
import time
from pathlib import Path

from modelmetis.dsp_packet import digest
from modelmetis.dsp_report import STYLE, THEME
from modelmetis.visual_audio import canonical_json


def preview(job_path, output):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    body = job["body"]
    if digest(canonical_json(body)) != job["body_sha256"]:
        raise ValueError("Prepared request integrity mismatch.")
    parts = body["messages"][1]["content"]
    context = json.loads(parts[0]["text"])
    condition_by_reference = {
        reference: condition for condition, reference in context["known_conditions"].items()
    }
    sections = []
    current_id = None
    image_id = None
    image_count = 0
    for part in parts[1:]:
        if part["type"] == "text":
            try:
                packet = json.loads(part["text"])
            except json.JSONDecodeError:
                image_id = part["text"]
                continue
            if current_id is not None:
                sections.append("</section>")
            current_id = packet["id"]
            role = "Query" if current_id == context["query"] else "Reference"
            condition = condition_by_reference.get(current_id)
            suffix = f" / {condition}" if condition else " / condition withheld"
            metrics = packet["measurement"]
            title = html.escape(f"{role} {current_id}{suffix}")
            sections.append(f'<section id="{html.escape(current_id)}"><h2>{title}</h2>')
            sections.append(
                '<div class="metrics">'
                f"<span><strong>{metrics['duration_seconds']:g} s</strong>Interval</span>"
                f"<span><strong>{metrics['rms_db_re_1_fs']:.3f} dB</strong>RMS re 1 FS</span>"
                f"<span><strong>{metrics['peak_fs']:.4f}</strong>Peak FS</span></div>"
            )
            sections.append(
                '<h3>FFT peaks</h3><div class="table-scroll"><table>'
                "<tr><th>Frequency (Hz)</th><th>Amplitude (FS peak)</th>"
                "<th>Amplitude (dB)</th></tr>"
            )
            for peak in metrics["peaks"]:
                sections.append(
                    f"<tr><td>{peak['frequency_hz']:g}</td>"
                    f"<td>{peak['amplitude_fs_peak']:.6g}</td>"
                    f"<td>{peak['amplitude_db_re_1_fs_peak']:.3f}</td></tr>"
                )
            sections.append("</table></div>")
            sections.append(
                "<details><summary>Exact measurement packet</summary><pre>"
                + html.escape(json.dumps(packet, indent=2))
                + "</pre></details>"
            )
        elif part["type"] == "image_url":
            url = part["image_url"]["url"]
            if not url.startswith("data:image/png;base64,") or current_id is None:
                raise ValueError("Expected local PNG evidence inside a packet.")
            image_count += 1
            sections.append(
                f'<figure><img width="1200" height="700" '
                f'alt="{html.escape(image_id or current_id)}" '
                f'src="{html.escape(url, quote=True)}"><figcaption>'
                f"{html.escape(image_id or current_id)} / original PNG / "
                f"detail={html.escape(part['image_url']['detail'])}"
                "</figcaption></figure>"
            )
    if current_id is not None:
        sections.append("</section>")
    navigation = " ".join(
        f'<a href="#{reference}">{reference} / {condition}</a>'
        for condition, reference in context["known_conditions"].items()
    )
    navigation += f' <a href="#{context["query"]}">{context["query"]} / query</a>'
    shared = html.escape(json.dumps(context, indent=2))
    schema = html.escape(json.dumps(body["response_format"], indent=2))
    prompt = html.escape(body["messages"][0]["content"])
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>DSP comparison | Exact model evidence</title>{THEME}<style>{STYLE}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.45;}"
        "</style></head><body><header><h1>DSP comparison packet</h1>"
        f"<p>{len(context['known_conditions'])} references + 1 query / {image_count} images / "
        f"{job['text_bytes']:,} UTF-8 text bytes / {job['request_bytes']:,} request bytes.</p>"
        "<p>Outcomes: known condition, outside-reference, indeterminate. "
        "Digital levels are not acquisition-calibrated.</p>"
        f"<nav>{navigation}</nav></header><main><details><summary>Shared units and configuration"
        f"</summary><pre>{shared}</pre></details><details><summary>Model instructions</summary>"
        f"<pre>{prompt}</pre></details>{''.join(sections)}"
        f"<details><summary>Required response schema</summary><pre>{schema}</pre></details>"
        "</main></body></html>"
    )
    with Path(output).open("x", encoding="utf-8") as stream:
        stream.write(page)
    return {"images": image_count, "output": str(output), "body_sha256": job["body_sha256"]}


if __name__ == "__main__":
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Preview an exact immutable DSP model request.")
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(preview(args.job, args.output)))
    finally:
        print(f"CommandElapsedSeconds={time.perf_counter() - started:.6f}")
