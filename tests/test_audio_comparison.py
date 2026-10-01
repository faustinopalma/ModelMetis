import base64
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from modelmetis.dsp_report import generate_report
from scripts.audio_comparison import load_dataset, pack_record, sha256


def test_audio_and_figures_match_registered_report(tmp_path):
    source = tmp_path / "source.wav"
    clock = np.arange(800) / 16000
    sf.write(source, 0.1 * np.sin(2 * np.pi * 500 * clock), 16000)
    report = tmp_path / "reports/R01"
    generate_report(source, report)
    item = {"id": "R01", "wav": str(source), "audio_sha256": sha256(source.read_bytes())}
    packed = pack_record(tmp_path, item)
    assert base64.b64decode(packed["audio"].split(",", 1)[1]) == source.read_bytes()
    assert packed["duration"] == 0.05 and packed["rate"] == 16000
    assert {"levels", "fft", "welch", "stft"}.issubset(packed["figures"])
    assert "source.wav" not in json.dumps(packed)
    for key, image in packed["figures"].items():
        assert sha256(base64.b64decode(image.split(",", 1)[1])) == packed["figureHashes"][key]
    with pytest.raises(ValueError, match="registered WAV"):
        pack_record(tmp_path, {**item, "audio_sha256": "modified"})


def test_changed_registration_is_rejected_before_loading_audio(tmp_path):
    (tmp_path / "sealed").mkdir()
    (tmp_path / "protocol.json").write_text("{}")
    (tmp_path / "sealed/truth.json").write_text("{}")
    (tmp_path / "registration.json").write_text(
        json.dumps(
            {
                "protocol_sha256": "changed",
                "truth_sha256": sha256(b"{}"),
            }
        )
    )
    with pytest.raises(ValueError, match="registration changed"):
        load_dataset(tmp_path, "Fixture")


def test_model_comparison_uses_the_same_reference_set(tmp_path, monkeypatch):
    from scripts import audio_comparison

    (tmp_path / "sealed").mkdir()
    protocol = {
        "known": [{"id": "R01", "condition_id": "C01", "label": "healthy"}],
        "queries": [{"id": "T01", "role": "final"}],
    }
    protocol_bytes = json.dumps(protocol).encode()
    truth_bytes = json.dumps({"T01": {"condition_id": "C01"}}).encode()
    (tmp_path / "protocol.json").write_bytes(protocol_bytes)
    (tmp_path / "sealed/truth.json").write_bytes(truth_bytes)
    (tmp_path / "registration.json").write_text(
        json.dumps(
            {
                "protocol_sha256": sha256(protocol_bytes),
                "truth_sha256": sha256(truth_bytes),
            }
        )
    )
    monkeypatch.setattr(
        audio_comparison,
        "pack_record",
        lambda folder, item: {"id": item["id"], "audioHash": item["id"]},
    )
    for phase in ("final", "novelty", "replay-known", "replay-novelty"):
        path = tmp_path / "round-02" / phase / "T01/03_response"
        path.mkdir(parents=True)
        (path / "attempt.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "decision": {"condition_id": "C01", "outcome": "similar"},
                }
            )
        )
    packed = load_dataset(tmp_path, "Fixture")
    assert [model["phase"] for model in packed["queries"][0]["models"]] == ["final", "replay-known"]


def test_generated_page_is_direct_reference_review(tmp_path, monkeypatch):
    from scripts import audio_comparison

    monkeypatch.setattr(
        audio_comparison,
        "load_dataset",
        lambda folder, name: {
            "name": name,
            "key": name,
            "protocolHash": "fixture",
            "references": [{"audioHash": "reference"}],
            "queries": [{"audioHash": "query"}],
        },
    )
    monkeypatch.setattr(audio_comparison, "load_icons", lambda: {})
    output = tmp_path / "review"
    audio_comparison.build(output)
    manifest = json.loads((output / "manifest.json").read_text())
    page = (output / "index.html").read_text()
    assert manifest["mode"] == "reference-review"
    assert "always visible" in manifest["labels"]
    assert 'id="correct-reference"' in page
    assert 'id="model-reference"' in page
    assert 'aria-label="Reference choice"' in page
    assert 'id="reference-match"' in page
    assert all(f'id="{identifier}"' not in page for identifier in ("choice", "record", "reveal"))
    assert "modelmetis-reference-review-" in page
    assert "modelmetis-human-comparison-" not in page
    assert 'id="model-status"' in page
    assert 'id="errors-only"' in page
    assert 'id="trial"' in page
    assert 'id="error-kind"' in page
    assert page.index('id="decision-top"') < page.index('id="views"')
    assert page.index('id="models"') < page.index('id="query-image"')
    assert page.count('id="model-status"') == 1
    assert ".tabs{display:flex;flex-wrap:nowrap;" in page


def test_model_error_categories_exclude_technical_failures():
    from scripts.audio_comparison import TEMPLATE

    source = TEMPLATE.read_text(encoding="utf-8")
    helpers = source.split("function modelResult(model,truth) {", 1)[1].split("const trialKey", 1)[
        0
    ]
    program = (
        "function modelResult(model,truth) {"
        + helpers
        + """
const assert = require('node:assert/strict');
const cases = [
    [{status:'completed',outcome:'similar',condition:'C01'}, 'correct', false],
    [{status:'completed',outcome:'similar',condition:'C02'}, 'wrong_class', true],
    [{status:'completed',outcome:'forced',condition:'C01'}, 'correct', false],
    [{status:'completed',outcome:'forced',condition:'C02'}, 'wrong_class', true],
    [{status:'unavailable',outcome:null,condition:null}, 'unavailable', false],
    [{status:'completed',outcome:'different',condition:null}, 'false_rejection', true],
    [{status:'technical_failure',outcome:'similar',condition:'C02'}, 'technical_failure', false],
    [{status:'completed',outcome:null,condition:null}, 'technical_failure', false],
];
for(const [model, expected, error] of cases){
    assert.equal(modelResult(model,'C01'),expected);
    assert.equal(isModelError(model,'C01'),error);
}
const wrong={status:'completed',outcome:'similar',condition:'C02'};
const rejected={status:'completed',outcome:'different',condition:null};
assert.equal(errorMatches(wrong,'C01','wrong'),true);
assert.equal(errorMatches(wrong,'C01','review'),false);
assert.equal(errorMatches(rejected,'C01','wrong'),false);
assert.equal(errorMatches(rejected,'C01','review'),true);
assert.equal(modelResult(rejected,'different'),'correct_rejection');
assert.equal(isModelError(rejected,'different'),false);
assert.equal(modelResult(wrong,'different'),'wrong_acceptance');
assert.equal(errorMatches(wrong,'different','wrong'),true);
assert.equal(errorMatches({status:'unavailable'},'C01','review'),false);
assert.equal(errorMatches({status:'technical_failure'},'C01','wrong'),false);
const references=[{condition:'C01'},{condition:'C02'}];
assert.equal(modelReferenceChoice([wrong],references).index,1);
assert.equal(modelReferenceChoice([{status:'completed',outcome:'forced',condition:'C01'}],references).index,0);
assert.equal(modelReferenceChoice([rejected],references).index,-1);
assert.match(modelReferenceChoice([rejected],references).reason,/rejected/);
assert.equal(modelReferenceChoice([wrong,wrong],references).index,-1);
assert.equal(modelReferenceChoice([],references).index,-1);
assert.equal(modelReferenceChoice([{status:'technical_failure',condition:'C02'}],references).index,-1);
assert.equal(modelReferenceChoice([{status:'completed',outcome:'similar',condition:'C99'}],references).index,-1);
"""
    )
    subprocess.run(["node", "-e", program], cwd=Path(__file__).resolve().parents[1], check=True)


def test_simple_review_cases_keep_model_choice_and_excluded_reference_explicit():
    from copy import deepcopy

    from scripts.dsp_extended_review import simple_review_data

    datasets = [{"name": "Fixture", "references": [
        {"id": "R01", "condition": "C01", "label": "healthy"},
        {"id": "R02", "condition": "C02", "label": "fault"}], "queries": [
            {"id": "Q01", "truth": "C01", "models": ["unused numeric controls"]},
            {"id": "Q02", "truth": "C02", "models": []}]}]
    original = deepcopy(datasets)
    rows = [{"name": "known", "dataset": "Fixture", "query_id": "Q01", "phase": "known",
             "predicted": "different", "expected": "C01", "category": "False rejection"},
            {"name": "excluded", "dataset": "Fixture", "query_id": "Q01", "phase": "excluded",
             "predicted": "C02", "expected": "different", "category": "Wrong acceptance"}]
    packed, cases = simple_review_data(datasets, rows)
    assert datasets == original
    assert len(packed[0]["queries"]) == 1
    assert "models" not in packed[0]["queries"][0]
    assert cases[0]["modelOutcome"] == "other"
    assert cases[0]["modelReferenceId"] is None
    assert cases[0]["correctReferenceId"] == "R01"
    assert cases[0]["visibleReferenceIds"] == ["R01", "R02"]
    assert cases[1]["correctClassExcluded"]
    assert cases[1]["correctReferenceId"] == "R01"
    assert cases[1]["modelReferenceId"] == "R02"
    assert cases[1]["visibleReferenceIds"] == ["R02"]
    with pytest.raises(ValueError, match="excluded"):
        simple_review_data(datasets, [{**rows[1], "predicted": "C01"}])
    with pytest.raises(ValueError, match="nonempty"):
        simple_review_data(datasets, [])


def test_simple_reference_choice_keeps_other_separate_from_browsable_bank():
    template = (
        Path(__file__).resolve().parents[1] / "scripts/templates/audio_comparison_simple.html"
    )
    source = template.read_text(encoding="utf-8")
    helper = source.split("function referenceChoice(", 1)[1].split("function addOption", 1)[0]
    program = "function referenceChoice(" + helper + """
const assert=require('node:assert/strict');
const refs=[{id:'R01'},{id:'R02'}];
const assigned={modelOutcome:'class',modelReferenceId:'R02',correctReferenceId:'R01'};
const other={...assigned,modelOutcome:'other',modelReferenceId:null};
assert.equal(referenceChoice(assigned,refs,'model').index,1);
assert.equal(referenceChoice(assigned,refs,'correct').index,0);
assert.equal(referenceChoice(other,refs,'model').index,-1);
assert.match(referenceChoice(other,refs,'model').reason,/Other.*no reference/);
assert.equal(referenceChoice(other,refs,'correct').index,0);
assert.equal(refs.length,2);
"""
    subprocess.run(["node", "-e", program], check=True)
    assert 'id="trial"' not in source and 'id="group"' not in source
    assert 'id="previous-reference"' in source and 'id="next-reference"' in source
    assert 'aria-describedby="model-choice-reason"' in source
    assert source.index('id="decision-top"') < source.index('class="pair"')


def test_pruned_review_keeps_unsafe_repeat_and_only_retained_display_views():
    from copy import deepcopy

    from scripts.dsp_pruned_review import DISPLAY_VIEWS, review_payload

    figures = {key: "image" for key in (*DISPLAY_VIEWS, "bands", "ridge", "autocorrelation")}
    datasets = [{"name": "Fixture", "references": [
        {"id": "R01", "condition": "C01", "label": "healthy", "figures": figures},
        {"id": "R06", "condition": "C06", "label": "other", "figures": figures}],
        "queries": [{"id": "Q01", "truth": "C01", "figures": figures}]}]
    snapshot = deepcopy(datasets)
    common = {"dataset": "Fixture", "query_id": "Q01", "phase": "known",
              "arm": "mask111", "removed": ["bands", "ridge", "autocorrelation"],
              "source_case": "source", "expected": "C01",
              "receipt": {"decision": {"explanation": "Recorded explanation."}}}
    rows = [{**common, "name": "primary", "block": "factorial", "predicted": "different",
             "category": "False rejection"},
            {**common, "name": "repeat", "block": "replicate", "predicted": "C06",
             "category": "Wrong class"}]
    payload = review_payload(datasets, rows)
    assert datasets == snapshot
    assert [case["attemptLabel"] for case in payload["cases"]] == ["Repeat", "Primary"]
    assert all(case["repeatWarning"] for case in payload["cases"])
    assert payload["cases"][0]["modelReferenceId"] == "R06"
    assert payload["cases"][1]["modelReferenceId"] is None
    assert set(payload["datasets"][0]["queries"][0]["figures"]) == set(DISPLAY_VIEWS)
    with pytest.raises(ValueError, match="triple-removal"):
        review_payload(datasets, [{**rows[0], "removed": ["bands"]}])


def test_public_review_assets_are_hash_bound_deduplicated_and_payload_is_exact(tmp_path):
    import base64
    import hashlib
    import json

    from scripts.publish_evidence import PayloadParser, publish_asset

    content = b"fixture-media"
    expected = hashlib.sha256(content).hexdigest()
    url = "data:audio/wav;base64," + base64.b64encode(content).decode()
    first = publish_asset(url, expected, "audio/wav", tmp_path)
    second = publish_asset(url, expected, "audio/wav", tmp_path)
    assert first == second and len(list((tmp_path / "media").iterdir())) == 1
    assert (tmp_path / first).read_bytes() == content
    with pytest.raises(ValueError, match="recorded hash"):
        publish_asset(url, "wrong", "audio/wav", tmp_path)
    with pytest.raises(ValueError, match="embedded"):
        publish_asset("https://example.com/audio.wav", expected, "audio/wav", tmp_path)
    encoded = json.dumps({"value": "A & B", "cases": []})
    page = '<script>0</script><script id="comparison-data" type="application/json">'
    page += encoded + '</script><script>const after=2;</script>'
    assert PayloadParser().extract(page) == (encoded, json.loads(encoded))
    with pytest.raises(ValueError, match="exactly one"):
        PayloadParser().extract(page + '<script id="comparison-data">{}</script>')


def test_publication_gate_limits_audio_and_avoids_task_slug_false_positive():
    from scripts.check_publication import findings

    audio = "examples/audio-comparison/media/" + "a" * 64 + ".wav"
    assert not findings(audio, b"fixture")
    assert "forbidden_artifact_path" in findings("examples/unreviewed.wav", b"fixture")
    assert "forbidden_artifact_path" in findings("outputs/response.json", b"{}")
    assert not findings("docs/example.md", b"task-first-shot-unsupervised-anomaly-detection")
    assert "openai_token" in findings("config.json", ("sk-" + "A" * 30).encode())


def test_public_example_links_cannot_escape_snapshot(tmp_path):
    from scripts.check_examples import local_target

    (tmp_path / "index.html").write_text("Example", encoding="utf-8")
    assert local_target(tmp_path, tmp_path / "index.html", "index.html") == (
        tmp_path / "index.html"
    )
    assert local_target(tmp_path, tmp_path / "index.html", "https://example.com") is None
    with pytest.raises(ValueError, match="escaping"):
        local_target(tmp_path, tmp_path / "index.html", "../private.json")
