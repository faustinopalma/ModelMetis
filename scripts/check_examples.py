import argparse
import hashlib
import json
import re
import wave
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.check_publication import findings


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
    comparison = [(path, parser) for path, parser in pages if parser.payload]
    if len(comparison) != 1:
        raise ValueError("Expected exactly one current comparison.")
    path, parser = comparison[0]
    payload = json.loads("".join(parser.payload))
    for dataset in payload["datasets"]:
        for record in [*dataset["references"], *dataset["queries"]]:
            audio = local_target(root, path, record["audio"])
            if hashlib.sha256(audio.read_bytes()).hexdigest() != record["audioHash"]:
                raise ValueError("Audio provenance mismatch.")
            for view, target in record["figures"].items():
                figure = local_target(root, path, target)
                if hashlib.sha256(figure.read_bytes()).hexdigest() != record["figureHashes"][view]:
                    raise ValueError("Figure provenance mismatch.")
    if len(payload["cases"]) != 10:
        raise ValueError("The public comparison must retain eight primaries and two repeats.")
    for case in payload["cases"]:
        response = json.loads(local_target(root, path, case["responseLink"]).read_text("utf-8"))
        if response["decision"]["explanation"] != case["explanation"]:
            raise ValueError("Displayed explanation differs from published decision.")
    outcomes = json.loads((root / "results/pruning-decisions.json").read_text("utf-8"))
    if len(outcomes) != 46 or len({row["name"] for row in outcomes}) != 46:
        raise ValueError("The crossed-study outcome set is incomplete.")
    return {"status": "passed", "files": len(entries), "audio_files": audio_count,
            "comparison_decisions": 10, "crossed_decisions": 46, "html_links": link_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify the public static evidence snapshot.")
    parser.add_argument("--root", type=Path, default=Path("examples"))
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))