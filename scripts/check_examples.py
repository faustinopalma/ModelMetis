import argparse
import hashlib
import json
import re
import wave
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.check_publication import findings

COMPARISONS = {"audio-comparison/index.html": 48, "archive/pruning-candidate/index.html": 10}


class PublicPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.links = []
        self.capture = False
        self.payload = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.links.extend(attrs[key] for key in ("href", "src") if attrs.get(key))
        if tag == "script" and attrs.get("id") == "comparison-data":
            self.capture = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.payload.append(data)


def local_target(root, source, target):
    parsed = urlsplit(target)
    if parsed.scheme in {"https", "http", "mailto"} or not parsed.path:
        return None
    if parsed.scheme or parsed.netloc:
        raise ValueError("Unsupported link scheme in public example.")
    destination = (source.parent / unquote(parsed.path)).resolve()
    if not destination.is_relative_to(root.resolve()) or not destination.is_file():
        raise ValueError(f"Broken or escaping example link: {source.name} -> {target}")
    return destination


def verify(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["files"]
    if not entries:
        raise ValueError("Refusing empty public evidence manifest.")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*")
              if path.is_file() and path != root / "manifest.json"}
    if set(entries) != actual:
        raise ValueError("Public files differ from the sealed manifest.")
    audio_count, pages, link_count = 0, [], 0
    for name, expected in entries.items():
        path = local_target(root, root / "index.html", name)
        if path is None:
            raise ValueError("Manifest requires local files.")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Changed public file: {name}")
        if path.suffix in {".html", ".json", ".md"}:
            if findings("examples/" + name, content):
                raise ValueError(f"Credential-pattern finding in public file: {name}")
            text = content.decode("utf-8")
            if re.search(r"(?i)(?:[a-z]:[\\/](?:code|users)[\\/]|\.azure[\\/])", text):
                raise ValueError(f"Local machine path in public file: {name}")
        if path.parent.name == "media" and path.stem != expected:
            raise ValueError("Media filename is not its content hash.")
        if path.suffix == ".wav":
            with wave.open(str(path), "rb") as audio:
                if audio.getnchannels() != 1 or audio.getnframes() == 0:
                    raise ValueError("Expected nonempty mono public audio.")
            audio_count += 1
        if path.suffix == ".html":
            parser = PublicPage()
            parser.feed(content.decode("utf-8"))
            pages.append((path, parser))
            for target in parser.links:
                local_target(root, path, target)
                link_count += 1
    comparisons = {path.relative_to(root.resolve()).as_posix(): parser
                   for path, parser in pages if parser.payload}
    if set(comparisons) != set(COMPARISONS):
        raise ValueError("Expected the current comparison and the archived pruning review.")
    decisions = {}
    for name, parser in comparisons.items():
        path = root.resolve() / name
        payload = json.loads("".join(parser.payload))
        for dataset in payload["datasets"]:
            for record in [*dataset["references"], *dataset["queries"]]:
                audio = local_target(root, path, record["audio"])
                if hashlib.sha256(audio.read_bytes()).hexdigest() != record["audioHash"]:
                    raise ValueError("Audio provenance mismatch.")
                for view, target in record["figures"].items():
                    figure = local_target(root, path, target)
                    if (hashlib.sha256(figure.read_bytes()).hexdigest()
                            != record["figureHashes"][view]):
                        raise ValueError("Figure provenance mismatch.")
        if len(payload["cases"]) != COMPARISONS[name]:
            raise ValueError(f"Unexpected decision count in {name}.")
        for case in payload["cases"]:
            response = json.loads(local_target(root, path, case["responseLink"]).read_text("utf-8"))
            if response["decision"]["explanation"] != case["explanation"]:
                raise ValueError("Displayed explanation differs from published decision.")
            if case.get("inputLink"):
                model_input = json.loads(
                    local_target(root, path, case["inputLink"]).read_text("utf-8"))
                if model_input["source_request_sha256"] != response["source_request_sha256"]:
                    raise ValueError("Published input and decision belong to different requests.")
        decisions[name] = payload["cases"]
    summary = json.loads((root / "results/simple-method-summary.json").read_text("utf-8"))
    for collection in summary["collections"]:
        cases = [case for case in decisions["audio-comparison/index.html"]
                 if case["dataset"] == collection["collection"]]
        counts = {}
        for case in cases:
            counts[case["category"]] = counts.get(case["category"], 0) + 1
        expected = {key: value for key, value in collection.items()
                    if key not in {"collection", "configuration", "decisions"}}
        if counts != expected or len(cases) != collection["decisions"]:
            raise ValueError("Displayed decisions differ from the published summary.")
    attempts = json.loads((root / "results/simple-method-outcomes.json").read_text("utf-8"))
    if len(attempts) != summary["http_attempts"] or len(attempts) != 68:
        raise ValueError("The simple-method attempt record is incomplete.")
    outcomes = json.loads((root / "archive/results/pruning-decisions.json").read_text("utf-8"))
    if len(outcomes) != 46 or len({row["name"] for row in outcomes}) != 46:
        raise ValueError("The crossed-study outcome set is incomplete.")
    return {"status": "passed", "files": len(entries), "audio_files": audio_count,
            "comparison_decisions": {name: len(cases) for name, cases in decisions.items()},
            "simple_method_attempts": len(attempts), "crossed_decisions": 46,
            "html_links": link_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify the public static evidence snapshot.")
    parser.add_argument("--root", type=Path, default=Path("examples"))
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))