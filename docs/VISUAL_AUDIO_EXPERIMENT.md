# EXP-011: STFT Reference Comparison

## Registration

Registered September 29, 2026, before numerical predictions or visual inference. This is an exploratory, bounded development experiment with no agreed deployment error or coverage targets. It cannot authorize promotion. Only STFT power spectrograms may be shown to the visual model. Welch is a numerical control only. Earlier representation alternatives in the handoff are superseded for this experiment.

Hypothesis: one publisher-confirmed reference per known condition can support recognition on a different physical drone and rejection when an entire condition is absent from the visible references. Publisher annotations simulate human references; they are not new physical diagnoses. A known condition may itself be a fault. Outside-reference does not establish a fault.

Dataset: Yi, Choi and Lee, Sound-Based Drone Fault Classification Using Multitask Learning, Zenodo version 1, DOI 10.5281/zenodo.7779574, CC BY 4.0. Use original, amplitude-preserving WAV/FLAC content from the previously audited A/B archives, never the historically peak-normalized exports. Recheck A/B archive SHA-256 against the September 19 audit, selected source PCM against the restricted inventory, and each selected file's decoder integrity. Do not read the C archive or query C rows.

Split whole drone groups before selecting clips or creating images: A supplies references, B supplies queries. Include exactly N (healthy), MF1 (motor-cap dent at position 1), PC1 (propeller cut at position 1), maneuver F, mic1, with an exact mic2 counterpart in the existing inventory. Select the lowest PCM SHA-256, then source path, per drone/condition. Selection is deterministic and independent of prediction outcomes. Assign opaque C01/C02/C03 IDs to these three conditions. Keep source filenames, labels, physical identities, hashes and offsets outside model messages.

There are six clips but only two physical drone groups and one query drone. These are heterogeneous hardware types, not replicated units of one model. Original take/segment lineage is unknown; shared synthetic backgrounds may confound transfer. B has already been used for development. The three query clips and their repeated fold appearances are not independent acquisition replicates. This screen establishes neither unseen-noise performance nor within-model population accuracy. Half-second clips cannot validate long-recording segmentation. No new physical independence claim is made.

Render all six clips with [the frozen configuration](../configs/visual-audio-stft-v1.json): mono 16 kHz, 0.5-second nonoverlapping windows, periodic Hann length/FFT 512, hop 64, linear 0-8,000 Hz and 0-0.5 s axes, one-sided PSD, reference 1 FS squared/Hz, fixed -110 to -10 dB color range, cividis, 1024 by 768 lossless RGB PNG, 128 dpi. These are digital full-scale units, not calibrated sound-pressure units. No per-record peak normalization, DC removal, automatic color limits or implicit resampling. STFT frames have no boundary extension; 32 ms frames and 4 ms steps leave edge regions without a full centered observation. Retain all fixed windows and tails, shade zero-padded time, report valid samples, silence and clipping. Never infer homogeneous regimes from a fixed window.

Schedule: one all-known fold with three visible references and all three B queries; then three leave-one-condition-out folds with two visible references and the same three B queries. Exclude each condition entirely from the images and text of its holdout fold. Total: 12 query/fold decisions, nine known trials, three unknown trials, three distinct query clips. Every reference set contains one recording per visible condition. No refitting, prompt search, extra reference labeling or query-driven threshold selection.

Numerical control: mean Welch PSD using exactly the same decoded samples, window, FFT, hop and frequency interval; fixed log10 conversion and clipping to the rendering dB limits, no amplitude normalization. Distance is RMS dB difference across frequency bins. Return outside_reference if the nearest distance exceeds 12 dB; otherwise indeterminate if the nearest/second-nearest gap is below 2 dB; otherwise accept the closest visible reference. These arbitrary frozen exploratory thresholds are not calibrated operating limits. No query labels select them and no extra labeled calibration examples are used.

Visual candidate: Azure OpenAI gpt-5.6-luna, version 2026-07-09. The authorized resource's catalog also lists sol and terra at that version; neither is substituted. Official model documentation lists image processing and structured outputs for Luna. The authorized ModelMetis resource currently deploys only gpt-audio-1.5@2026-02-23; there is no verified GPT-5.6 endpoint. Therefore no real visual call is authorized by this registration alone. Prepared messages use metadata-free STFT data URLs, neutral reference IDs, a query image, stateless context and detail=high. Actual provider resizing, image readability after provider processing, structured-output compatibility, latency and prices remain blocked until deployment/access verification. Generic vision documentation is not proof of Luna's effective preprocessing.

Future live gate for this same bounded design: verify fixed model/version, provider access, image/detail behavior and current price source; record a separate immutable execution authorization before sending anything. At most one two-image synthetic STFT transport probe and twelve real requests; no retries, no alternate model, at most 120 seconds per request and 1,800 seconds for the run, output at most 512 tokens per request. Stop on a transport, parser, identity or rendering-integrity failure. Synthetic signals validate mechanics only. Unsent requests are not technical inference failures or model abstentions.

Report correct-known, wrong-known, known false rejection, unknown false acceptance, correct unknown rejection, indeterminate and technical failure separately; include denominators, confusion table, per-condition results, accepted-label error, known-label coverage and decision coverage. With one query unit, do not produce IID confidence intervals or false-alerts-per-hour estimates. Record measured decode/render/control latency, actual image/token counts and cost where measured, and human reference/calibration/correction/audit work. Missing model usage is not a zero-error result. Do not convert accepted predictions into gold, silver, references or training data.

## Reproduction

The native ARM64 application runtime is used; the separate x64 ML runtime is unchanged. The exact additional renderer dependency snapshot is [requirements-visual-audio-windows-arm64.txt](../ml/requirements-visual-audio-windows-arm64.txt). Baseline: 120 tests passed in 13.18 s pytest time, 14.522 s wall time; Ruff clean. Three preexisting dependency warnings remain. All attempt outputs must use new directories and must never overwrite historical artifacts.

The [results report](VISUAL_AUDIO_RESULTS.md) records the offline outcome, all experimental attempts and the exact live-access blocker. The committed aggregate contains no sample-level source answers, credentials or private spending limits.

From the repository root, the following commands reproduce the bounded offline experiment with the existing A/B source archives and restricted audited inventory. Use fresh output directory names on every rerun; the commands refuse to overwrite an attempt. `Measure-Command` times each invocation and `Out-Host` retains its visible output. The Python CLI additionally records operation times in `attempts.jsonl`.

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.visual_audio prepare-drone --output data/visual-audio-exp011-replay-v1 | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.visual_audio compare-offline --prepared data/visual-audio-exp011-replay-v1 --output artifacts/visual-audio-exp011-replay-v1 | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.visual_audio evaluate --prepared data/visual-audio-exp011-replay-v1 --run artifacts/visual-audio-exp011-replay-v1 --output artifacts/visual-audio-exp011-replay-evaluation-v1 | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.preview_visual_audio --prepared data/visual-audio-exp011-replay-v1 --run artifacts/visual-audio-exp011-replay-v1 --output artifacts/visual-audio-exp011-replay-v1/preview.html | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m pytest -q tests/test_visual_audio.py | Out-Host }
```

For other recordings, use the reusable renderer with a JSON list containing exactly `path`, `recording_id`, `group_id` and `split` per source. Paths resolve relative to the manifest. Assign physical acquisition groups and split them before calling the renderer; duplicated group IDs across splits are rejected. Do not infer independent acquisition IDs from window numbers. Source filenames may remain in the provenance manifest but are never included in model messages.

```json
[
	{"path": "audio/opaque-01.wav", "recording_id": "R01", "group_id": "G01", "split": "support"},
	{"path": "audio/opaque-02.wav", "recording_id": "R02", "group_id": "G02", "split": "query"}
]
```

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.visual_audio render --manifest data/custom/manifest.json --config configs/visual-audio-stft-v1.json --output artifacts/custom-stft-v1 | Out-Host }
```

WAV/FLAC content is recognized independently of extension. Unsupported encodings are rejected. WAV container/chunk/sample lengths are checked; FLAC requires a declared frame count and an embedded PCM checksum, including checked FFmpeg fallback if libsndfile decoding fails. Float audio must be finite. Silent/clipped windows remain in the manifest as quality flags. Multichannel or mismatched-rate sources are rejected by default; explicit `mean` and `polyphase` configuration policies enable recorded transformations without peak normalization. Changing these policies creates a different rendering/reference version. Window offsets refer to the analysis sample rate, with original sample rate/frame count and transformation provenance retained.

The generic renderer returns all segment decisions' inputs and time offsets in its manifest; it does not diagnose a recording or aggregate a file-level label. The comparison command is intentionally offline and does not contain an unverified HTTP inference adapter. A live adapter must first pass the separately recorded model-access and transport gates.