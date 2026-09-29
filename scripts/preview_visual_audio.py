import argparse
import base64
import hashlib
import html
import json
import time
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EXP-011 | STFT model inputs</title>
<script>
(() => {
  const param = new URLSearchParams(window.location.search).get("scoutTheme");
  const theme = param || (window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
</script>
<style>
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}
* { box-sizing: border-box; letter-spacing: 0; }
body { margin: 0; padding: 24px; background: var(--cp-surface-soft); color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif; }
main { max-width: 1600px; margin: auto; }
header { border-bottom: 1px solid var(--cp-border); padding-bottom: 16px; }
h1 { font-size: 28px; margin: 0 0 8px; }
h2 { font-size: 19px; margin: 24px 0 12px; }
p { margin: 6px 0; color: var(--cp-text-muted); }
.status { color: var(--cp-accent); font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
figure { margin: 0; min-width: 0; }
figcaption { padding: 0 0 8px; font-weight: 600; }
.image { width: 100%; border: 1px solid var(--cp-border); padding: 0; display: block;
  background: var(--cp-surface); cursor: zoom-in; aspect-ratio: 4 / 3; }
img { width: 100%; height: auto; aspect-ratio: 4 / 3; display: block; }
button:focus-visible { outline: 3px solid var(--cp-link); outline-offset: 3px; }
dialog { max-width: 98vw; max-height: 96vh; padding: 16px; border: 1px solid var(--cp-border);
  background: var(--cp-surface); color: var(--cp-text); }
dialog::backdrop { background: var(--cp-overlay); }
dialog img { width: 1024px; max-width: 90vw; }
dialog button { display: block; margin-left: auto; margin-bottom: 8px; padding: 8px 16px;
  border: 1px solid var(--cp-border); background: var(--cp-surface-soft); color: var(--cp-text); }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } body { padding: 16px; } }
</style></head><body><main>
<header><h1>EXP-011 / STFT model inputs</h1>
<p class="status">Prepared only. No visual model inference has run.</p>
<p>16 kHz mono | 0.5 s | Hann 512 / hop 64 | 0-8 kHz | -110 to -10 dB re 1 FS^2/Hz</p>
<p>Original lossless PNGs: 1024 x 768. Query diagnoses withheld.</p></header>
@@FIGURES@@
</main><dialog aria-label="Full-resolution STFT image"><button type="button">Close</button>
<img alt=""></dialog>
<script>
const dialog = document.querySelector("dialog");
for (const button of document.querySelectorAll(".image")) {
  button.addEventListener("click", () => {
    const original = button.querySelector("img");
    dialog.querySelector("img").src = original.src;
    dialog.querySelector("img").alt = original.alt;
    dialog.showModal();
  });
}
dialog.querySelector("button").addEventListener("click", () => dialog.close());
</script></body></html>
"""


def preview(prepared, run, output):
    prepared, run, output = Path(prepared), Path(run), Path(output)
    inputs = json.loads((prepared / "inputs.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "images/manifest.json").read_text(encoding="utf-8"))
    records = {row["recording_id"]: row for row in manifest["recordings"]}
    sections = []
    groups = [
        ("References", [(f"Reference {row['condition_id']}", row["recording_id"])
                        for row in inputs["supports"]]),
        ("Queries", [(f"Query {number:02}", identifier)
                     for number, identifier in enumerate(inputs["queries"], 1)]),
    ]
    for heading, items in groups:
        figures = []
        for title, identifier in items:
            windows = records[identifier]["windows"]
            if len(windows) != 1:
                raise ValueError("This preview requires one window per registered recording.")
            image = windows[0]
            payload = (run / "images" / image["image"]).read_bytes()
            if hashlib.sha256(payload).hexdigest() != image["image_sha256"]:
                raise ValueError("Image changed since rendering.")
            uri = "data:image/png;base64," + base64.b64encode(payload).decode("ascii")
            title = html.escape(title, quote=True)
            figures.append(f'<figure><figcaption>{title}</figcaption><button class="image" '
                           f'title="Enlarge {title}" aria-label="Enlarge {title}">'
                           f'<img src="{uri}" alt="{title} STFT spectrogram" '
                           'width="1024" height="768"></button></figure>')
        sections.append(f'<section><h2>{heading}</h2><div class="grid">'
                        + "".join(figures) + "</div></section>")
    with output.open("x", encoding="utf-8") as stream:
        stream.write(TEMPLATE.replace("@@FIGURES@@", "".join(sections)))
    return {"images": sum(len(items) for _, items in groups), "output": str(output),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Preview exact prepared STFT PNGs locally.")
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(preview(args.prepared, args.run, args.output)))
    finally:
        print(f"ElapsedSeconds={time.perf_counter() - started:.6f}")