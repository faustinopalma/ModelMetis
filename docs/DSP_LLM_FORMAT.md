# DSP Evidence Packets For Reference Comparison

This page preserves the historical interval-packet format. The restarted N-known-plus-one-unknown workflow sends complete generated reports and uses a binary similarity decision; see [Whole-Report DSP Similarity](DSP_REPORT_COMPARISON.md) for its implementation, inspectable output folder and first real response.

Each reference/query packet contains typed DSP measurements and two original images: FFT amplitude and STFT power density. Requests contain 16-22 KB of text, six or eight images and at most 1.07 MB total. [EXP-012](DSP_LLM_RESULTS.md) completed technically but recognized 0/9 known-condition trials. Image selection has not been optimized or independently validated for diagnosis.

The [protocol](DSP_LLM_PROTOCOL.md) defines the experiment. The [DSP generator](DSP_PIPELINE.md), packet builder, model worker and sealed evaluator are separate components.

## Packet Contract

The [packet implementation](../src/modelmetis/dsp_packet.py) verifies the report manifest, evidence file, provenance binding and image hashes before constructing an input. Every image is the original metadata-free 1200 by 700 RGB PNG, not a screenshot of an HTML page or a thumbnail. The local packet preview is `artifacts/dsp-sol-exp012-prepared-v1/preview-v2.html`; it displays the same diagnostic text and eight PNGs as the first prepared request.

| Element | Sent to the model | Kept in the local audit |
| --- | --- | --- |
| Identity | R01/R02/R03 for references, Q01 for query; C01/C02/C03 for visible conditions | Original recording identity, physical group, source and PCM hashes, report manifest hash |
| Configuration | Common sample rate, interval length, FFT/STFT parameters, axes, scaling and units | Configuration/code/dependency hashes and environment versions |
| Measurements | RMS, peak, DC, crest factor, kurtosis, zero crossings, clipping/silence, FFT peaks, Welch density summary, band powers, envelope modulation and autocorrelation | Full numerical arrays and unrounded original report |
| Images | One original FFT plot, including its fixed 0-500 Hz detail; one original STFT plot; `detail=high` | PNG hashes, original report locations and source offsets |
| Quality/context | Unknown gain comparability, unverified regime homogeneity, declared prior signal processing and level-change candidate count | Query diagnoses, publisher source paths and evaluation truth |
| Output | Known condition, outside-reference or indeterminate; evidence citations and limitations | Raw response, usage, latency, parsed result and independent evaluator outcome |

Floats use seven significant digits, not a fixed number of decimal places: a small value such as `1.234568e-12` remains nonzero. Integer counts and null values remain exact. Original arrays and full precision are retained outside the prompt. The packet includes named units and nulls for undefined measurements; it does not translate digital full-scale units into sound-pressure levels or infer RPM/component geometry.

One packet covers one channel and one interval, not an entire long recording. A downstream long-recording workflow must preserve segment-level decisions and cannot turn a sampled overview or majority vote into evidence that every regime was inspected. EXP-012 uses half-second clips with one interval each. The four previous cross-dataset DSP demonstrations are not interchangeable reference classes; their hardware, processing and acquisition histories differ.

Before building a comparison, the implementation requires equal sampling rate, valid sample count, DSP configuration, generator/dependency versions, channel policy and declared source-processing history. Exact PCM duplicates are rejected. The experimental runner also checks that reference/query physical group IDs do not overlap. These are explicit checks, not proof that a caller's acquisition lineage is correct. A fresh microphone position, noise mixture or window index does not establish independence.

## Request Layout

The first text block contains the task, the complete visible condition/reference map, the query ID, shared configuration and units. Each subsequent packet contains a measurement ID and two image IDs. Text/image order is stable. A three-reference request uses eight images; a whole-condition holdout uses six. No previous model responses are included. The full HTML report, source provenance file, query truth and array archives are never copied into the request.

The following is a structural illustration; the generated request contains the actual measured values, original PNG data URLs and strict output schema:

```json
{
  "known_conditions": {"C01": "R01", "C02": "R02", "C03": "R03"},
  "query": "Q01",
  "packets": [
    {"id": "R01", "measurement_id": "R01.M01", "images": ["R01.I01", "R01.I02"]},
    {"id": "R02", "measurement_id": "R02.M01", "images": ["R02.I01", "R02.I02"]},
    {"id": "R03", "measurement_id": "R03.M01", "images": ["R03.I01", "R03.I02"]},
    {"id": "Q01", "measurement_id": "Q01.M01", "images": ["Q01.I01", "Q01.I02"]}
  ]
}
```

Required output fields are `outcome`, `condition_id`, `evidence_ids`, `explanation` and `limitations`. Azure strict structured output constrains the shape; local validation additionally checks that a known decision uses an actually visible condition, novelty/abstention uses null, and every cited evidence ID exists in this request. Refusals, truncated output, malformed JSON, fabricated citations, changed model identity and missing usage are distinct technical failures. An explanation or valid citation is not evidence of analytical correctness.

The exact model is `gpt-5.6-sol@2026-07-09`; no fallback to Luna, Terra, GPT Audio or another model is configured. Each request uses Chat Completions v1, low reasoning, at most 4,096 completion tokens including reasoning, strict JSON schema, no tools, no temperature parameter and no streaming. The [single-call worker](../src/modelmetis/dsp_inference.py) checks the live ARM model/version/SKU before acquiring a token and posting to the exact declared HTTPS endpoint. Credentials exist only in process memory and are never written into request/response files.

## Bounded Experiment

The [orchestrator](../scripts/dsp_experiment.py) creates a new immutable preparation directory and binds code, settings, jobs, source registration and sealed truth before sending anything. It reuses the existing three references and three queries from the EXP-011 A/B proxy and generates fresh deterministic DSP reports. No changes to EXP-011 artifacts or DSP code are required. One synthetic gate is permitted, followed by at most twelve real requests. A failed gate or first technical error stops the phase; there are no automatic retries. Each worker has a 180-second process deadline and each phase a 2,400-second scheduling deadline. A timed-out server call may still have executed; its cost/outcome stays unknown until reconciled, and it is not silently resubmitted.

Prepared registration: `dc94774abfc050044cccd60a40e9d67cbfa9d9e405e85ada8729d85b1a4c1c4b`. Text size ranges from 16,383 to 21,545 UTF-8 bytes; the largest complete JSON body is 1,064,263 bytes. Actual token counts require a provider response and are not inferred from byte counts. The first prepared body hash is `cc7761f3c9a3efa2664bc5a69a1ffcddd59dbe30b29c40897b5f9649ef3ea2f9`.

The public Data Zone Standard short-context prices consulted September 29 are USD 4.40 input, 0.44 cached input and 22 output per million tokens. The worker counts all completion tokens, including reasoning. Estimated cost is `(uncached_input * 4.40 + cached_input * 0.44 + completion * 22) / 1,000,000`; missing usage remains unknown. These are list-price estimates. [Price source](https://azure.microsoft.com/en-us/pricing/details/azure-openai/).

## Azure State

The original dedicated deployment in `rg-modelmetis-dev-dsp-swc` was still Creating/Running at its last saved read, with no model child or inference. Cancelling the 321-second local wait did not cancel ARM. A separate governance diagnostic deployment failed because its Log Analytics destination was absent; causality for the parent delay is unproven. The [readiness receipt](../ml/dsp-sol-exp012-status-v1.json) preserves that attempt. Obtain fresh state before further operations.

The completed experiment used a separately frozen [reuse preparation](DSP_RESOURCE_REUSE.md), pinned Sol and DataZoneStandard capacity 50. [Global Standard quota](DSP_GLOBAL_QUOTA.md) is a separate submitted request with unverified approval. Model versions, settings and preparations cannot be exchanged silently.

## Reproduction And Evidence

The native ARM64 worker uses HTTPX and an Entra token obtained through the existing CLI. It requires no Azure SDK installation or merge with the x64 ML runtime.

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_experiment prepare --output artifacts/dsp-sol-exp012-prepared-replay | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.preview_dsp_packet --job artifacts/dsp-sol-exp012-prepared-replay/jobs/01.json --output artifacts/dsp-sol-exp012-prepared-replay/preview.html | Out-Host }
```

These commands prepare offline evidence only. The live EXP-012 run is complete; further calls require a new protocol and readiness check. Preserve frozen code/settings and all earlier requests/responses. New output directories cannot bypass failed gates or request limits. Predictions do not enter reference sets or training automatically.

Tests cover image hashes, source-metadata exclusion, numeric preservation, mismatch/duplicate rejection, identity/citations and token accounting. Browser checks verified eight original 1200 by 700 PNGs and no horizontal overflow at 1440/390 pixels. Live API acceptance is recorded in the [results](DSP_LLM_RESULTS.md); provider-internal resizing and the images' independent contribution remain unmeasured.
