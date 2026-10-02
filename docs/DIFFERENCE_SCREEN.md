# Speed-Normalized Reports Recognize Best; Subtracting The Healthy Normal Does Not

**Reports normalized to shaft orders give the best recognition measured on these cases: 40/72 correct against 27/72 for the simple method's reports (paired p = 0.02), and the only arm that still works at a doubled speed (8/18 against 2/18).** Every reference and query passes through the [known-speed tool](../tools/audio_order_known/README.md), which resamples the audio to its measured shaft rotation, so rotation-locked components share one order axis whatever the speed. Stating the speed beside ordinary reports gives 33/72; normalization from a base frequency estimated in the audio gives 31/72, and 14/24 on the cases where every recording was normalized. Subtracting the healthy recording gives the same decisions as raw spectra when references and query share a regime and fewer when speed changes. Without a model, order spectra up to the 100th shaft order recognize 213 of 343 queries at 1.1 times the reference speed and 73 of 160 at double speed, against 78 and 21 for raw spectra. All counts come from one public test rig; the normalized arm's lead over stated speed (+21/-14, p = 0.31) still needs more cases.

## Method

Each recording becomes a gain-centered log-power spectrum. A query receives the class of the nearest single reference per class; the healthy class is a candidate. Six representations are compared on the same queries:

| Representation | Definition | Model-facing analog |
| --- | --- | --- |
| Raw | Welch spectrum, 1,024-sample frames, 20 Hz-20 kHz | Current simple method |
| Difference | Raw minus the healthy recording of the same regime; healthy references are the zero curve | [Difference protocol](DIFFERENCE_PROTOCOL.md) |
| Orders | Welch spectrum, 32,768-sample frames, frequency divided by the known shaft speed, 0.5-300 orders | Reports that state the shaft speed and an order axis |
| Difference on orders | Difference computed in Hz, then placed on the order axis | Both |
| Shift search | Log-frequency spectrum; distance minimized over shifts up to ±1.2 octaves | Telling the model that frequencies may be shifted, without the speed |
| Difference with shift search | Difference on the log-frequency grid with the same search | Both |

The datasets test three situations:

- **MAFAULDA:** one rig, ten classes (normal, imbalance, horizontal and vertical misalignment, three bearing defects in two positions). 400 seeded fault queries; references are one acquisition per class at a speed 1.0, 1.1, 1.3, 1.6 or 2.0 times the query's, the median severity of that cell. At ratio 1.0 the reference is a different acquisition with another severity. 167 files with microphone spikes are excluded. Shaft speed is the tachometer value, or 0.977 times the nominal file value when the tachometer estimate fails.
- **UORED:** bearing-disjoint. Each developing or faulty state of one bearing is compared with the same state of the other 19 bearings; each bearing's own healthy recording is its normal. Ball defects were recorded at 0 N and their healthy states at 400 N, so the difference carries a load change for that class.
- **Ottawa:** the historical case: profile-1 unloaded references at a 15 Hz drive, 14 profile-2 fault acquisitions at 30 Hz, with the healthy recording of each profile and load as the normal. Profiles 5 and 7 are excluded.

Chance is 1 in 10 for MAFAULDA, 1 in 5 for UORED and 1 in 8 for Ottawa.

## Results

| Data and scenario | Raw | Difference | Orders | Difference on orders | Shift search |
| --- | --- | --- | --- | --- | --- |
| MAFAULDA, same speed | 246/387 | 246/387 | 151/387 | 37/387 | 65/387 |
| MAFAULDA, speed x1.1 | 78/343 | 3/343 | 147/343 | 12/343 | 56/343 |
| MAFAULDA, speed x1.3 | 49/287 | 0/287 | 95/287 | 17/287 | 51/287 |
| MAFAULDA, speed x1.6 | 29/224 | 0/224 | 41/224 | 7/224 | 36/224 |
| MAFAULDA, speed x2 | 21/160 | 0/160 | 33/160 | 12/160 | 20/160 |
| UORED, other bearings, developing | 9/20 | 11/20 | 11/20 | 10/20 | 6/20 |
| UORED, other bearings, faulty | 7/20 | 9/20 | 10/20 | 6/20 | 7/20 |
| Ottawa, profile 1 to 2, faults | 2/14 | 3/14 | 3/14 | 0/14 | 1/14 |

Paired exact tests against raw on the same queries:

- **Orders improve every MAFAULDA speed change.** Gains/losses are +90/-21 at x1.1, +62/-16 at x1.3, +26/-14 at x1.6 and +19/-7 at x2. At the same speed they lose (+22/-117): rescaling also moves fixed-frequency content and the order axis uses finer, noisier spectra. Speed context should be added beside the Hz view, not replace it.
- **The difference equals raw at the same speed and loses under any speed change.** At equal regimes the two normals are the same recording, so the distances are identical. Under speed changes nearly every query lands on the healthy zero curve: the fault part of the difference is smaller than the mismatch between differences taken at two speeds. Without the healthy candidate it still ranks near raw (95/343 against 78/343 at x1.1; 25/160 against 24/160 at x2) and below orders.
- **Shift search without the speed does not help** (+34/-56 at x1.1, +35/-33 at x1.3, +14/-15 at x2).
- **UORED and Ottawa show no measurable difference.** All paired differences are at most four queries (p ≥ 0.375). The UORED ball gains of the difference coincide with its load confound. Ottawa stays near chance under every representation.

## Model Test: Normalized Reports Lead

The same pinned model as the simple method, GPT-5.6 Sol 2026-07-09 on Data Zone Standard with low reasoning effort, received six arms on identical cases. Every arm keeps the simple method's prompt and decision schema and adds one short guidance paragraph:

| Arm | What each request contains |
| --- | --- |
| Reports | Ten reference reports with class names and the query report |
| Speed context | The reports, each report's shaft frequency, an order-axis Welch figure per report and guidance that rotation-locked lines scale with speed while resonances stay in hertz |
| Healthy differences | The reports and a difference figure per report, its Welch spectrum minus the healthy recording at its own speed |
| Matched speed | Reports of references resampled so their shaft frequency equals the query's, with each reference's original and matched speed |
| Normalized, known speed | Reports from the [known-speed tool](../tools/audio_order_known/README.md) for every recording, using the tachometer shaft speed: original waveform, spectrum and spectrogram in hertz, then order spectrum, time-order map, angular envelope spectrum, cycle average and angular autocorrelation, with the tool's measurements |
| Normalized, estimated base | The same reports from the [estimated-base tool](../tools/audio_order_estimated/README.md), which finds the base frequency from harmonic peaks of each recording; recordings without an accepted base keep only their hertz figures and state the reason |

Cases were fixed with seed 20261001 before any call: for each speed ratio 1.0, 1.1, 1.3 and 2.0, two queries for each of the nine fault classes, with references chosen as in the screen. All 432 requests returned HTTP 200 with validated, cited decisions; rate-limit waits repeated identical request bytes and no other retry occurred. Recording names are withheld from every request.

| Arm | x1.0 | x1.1 | x1.3 | x2.0 | All |
| --- | --- | --- | --- | --- | --- |
| Reports | 10/18 | 9/18 | 6/18 | 2/18 | 27/72 |
| Speed context | 9/18 | 14/18 | 8/18 | 2/18 | 33/72 |
| Healthy differences | 9/18 | 12/18 | 6/18 | 2/18 | 29/72 |
| Matched speed | 10/18 | 11/18 | 6/18 | 2/18 | 29/72 |
| **Normalized, known speed** | **13/18** | 10/18 | **9/18** | **8/18** | **40/72** |
| Normalized, estimated base | 12/18 | 10/18 | 5/18 | 4/18 | 31/72 |
| Nearest raw spectrum, no model | 14/18 | 2/18 | 3/18 | 2/18 | 21/72 |
| Nearest order spectrum, no model | 8/18 | 7/18 | 6/18 | 3/18 | 24/72 |
| Nearest normalized order spectrum, no model | 6/18 | 8/18 | 6/18 | 8/18 | 28/72 |

The last row uses the known-speed tool's order spectra (0-20 orders, 0.125-order bins) with the same mean-centered decibel distance as the other numerical rows. Paired exact tests for the normalized known-speed arm: against reports +20/-7 (p = 0.02); against speed context +21/-14 (p = 0.31); against matched speed +21/-10 (p = 0.07); against the nearest raw spectrum +27/-8 (p = 0.002), +23/-3 on the 54 speed-changed cases. The model answered `different` at most 7 times in 72 decisions per arm; nearly every error is a wrong class. Four readings follow:

- **Normalization works because it aligns rotation-locked structure while keeping the hertz view.** The known-speed reports gain at equal speed too (13/18 against 10/18), where the angular figures add cycle-locked views the ordinary report lacks.
- **Normalization reaches a doubled speed.** It is the only arm, with or without a model, that recognizes more than 3/18 at x2: both the model (8/18) and the order-spectrum distance (8/18) benefit.
- **Whole-report resampling is the wrong normalization.** Matched speed moves fixed-in-hertz resonances and broadband shape together with the rotation-locked lines, and adds nothing over reports (+9/-7).
- **The estimated base approaches the known speed when it covers every recording.** Its accepted bases agreed with the tachometer within 3% on every calibration recording. With every recording of a case normalized it scored 14/24 against 16/24 for the known speed; cases with unnormalized recordings fell to 17/48.

The first three arms used 10,777,163 prompt and 994,021 completion tokens (about USD 59.53), matched speed about USD 21.78, and the two normalized arms 3,596,395 prompt and 627,463 completion tokens (about USD 26.19), at the configured list prices; these are estimates rather than invoices.

## Wider Order Range Recognizes Most Recordings Across Speed Changes

The same 400 seeded MAFAULDA queries as the screen were compared, without a model, using the known-speed tool's order spectrum. Extending the analysis from 20 to 100 shaft orders gives the strongest speed-changed recognition measured in this study:

| Speed ratio | Raw spectrum | Order spectrum (screen) | Tool, 0-20 orders | Tool, 0-100 orders | Angular envelope, 0-20 orders | Estimated base, 0-20 orders |
| --- | --- | --- | --- | --- | --- | --- |
| 1.0 | **246/387** | 151/387 | 132/387 | 217/387 | 192/387 | 117/387 |
| 1.1 | 78/343 | 147/343 | 106/343 | **213/343** | 113/343 | 85/343 |
| 1.3 | 49/287 | 95/287 | 78/287 | **137/287** | 102/287 | 68/287 |
| 1.6 | 29/224 | 41/224 | 61/224 | **104/224** | 73/224 | 58/224 |
| 2.0 | 21/160 | 33/160 | 51/160 | **73/160** | 52/160 | 38/160 |

The estimated-base column counts recordings without an accepted base as errors (37, 24, 18, 11 and 4 queries per row). At equal speed the hertz spectrum stays strongest, so the reports keep both views. The model arms above used the tool's default 0-20 orders; reports with 0-100 orders are the next arm to run.

The same representations on the other datasets show where normalization applies:

| Data | Raw spectrum | Order spectrum (screen) | Tool, 0-20 orders | Tool, 0-100 orders | Angular envelope |
| --- | --- | --- | --- | --- | --- |
| UORED, other bearings, developing | 9/20 | 11/20 | 11/20 | 13/20 | 8/20 |
| UORED, other bearings, faulty | 7/20 | 10/20 | 12/20 | 14/20 | 13/20 |
| Ottawa, profile 1 to 2 | 2/14 | 3/14 | 1/14 | 1/14 | 2/14 |
| FSTF, references at another of 600/1,200/1,800 rpm | **47/72** | 15/72 | 17/72 | 16/72 | 26/72 |

FSTF records one bearing per condition through one stethoscope or air microphone, so its fixed-in-hertz signature identifies each recording across speeds; there the hertz view carries the decision. Ottawa stays near chance in every view, consistent with its load and motor confounds. The estimated base was accepted for 798/895 MAFAULDA recordings (797 within 3% of the tachometer), 30/32 Ottawa recordings (29 within 3% of the drive frequency), 1/60 UORED and 0/36 FSTF recordings.

## The Tacholess Estimator Needs Calibrated Acceptance

The estimated-base tool's selected harmonic path tracked the MAFAULDA tachometer within 3% on every inspected recording, but its default acceptance thresholds (score 0.65, margin 0.08) accepted none of the 389 case recordings. Thresholds were therefore calibrated against the tachometer, without fault labels, on 200 seeded recordings outside every case: the most permissive grid point whose accepted bases all stay within 3% of the shaft speed was score 0.2 and margin 0, accepting 174/200, all within 3%. On the case recordings it accepted 339/389. The thresholds belong to this rig and microphone; another machine needs its own calibration against an independent speed measurement.

## Decision

Generate every reference report and the query report with the known-speed normalization tool whenever the shaft speed is measured, and keep the simple method's prompt, references and decision schema. Where no speed is measured, use the estimated-base tool with thresholds calibrated on that machine, and treat recordings without an accepted base as weaker evidence. Do not add healthy-normal differences or resample whole reports. Keep a numerical distance beside the reports: at equal speed the nearest raw spectrum (14/18) still matches the best model arm.

## Limits

MAFAULDA comes from one rig with one defective bearing per defect type; its queries are separate acquisitions, not separate machines. The model test has 18 cases per ratio and arm, so per-ratio differences of a few cases are within chance. The six arms were designed in sequence on the same 72 cases, so the normalized arms are a development result awaiting fresh cases or another machine. UORED and Ottawa screen denominators are 20 and 14. Each class has one reference per case, and the model's figures are contact-sheet thumbnails of the full reports plus at most one added figure per report. MAFAULDA states no reuse license; raw data stay local and only aggregate results are recorded.

## Reproduce

```powershell
python -m scripts.fetch_mendeley --dataset y2px5tg92h --version 5 --prefix 3_MatLab --output data/raw/uored-v5
python -m scripts.audit_mafaulda --download --output outputs/mafaulda-audit-new
python -m scripts.extract_mafaulda_microphone
python -m scripts.difference_screen --output outputs/difference-screen-new --mafaulda-audit outputs/mafaulda-audit-new/files.json
python -m pytest -q tests/test_difference_screen.py
python -m scripts.speed_context_experiment prepare --output outputs/speed-context-new --audit outputs/mafaulda-audit-new/files.json
python -m scripts.speed_context_experiment evaluate --output outputs/speed-context-v1
python -m scripts.speed_matched_experiment prepare --output outputs/speed-matched-new
python -m scripts.speed_normalized_experiment calibrate --output outputs/speed-normalized-new
python -m scripts.speed_normalized_experiment prepare --output outputs/speed-normalized-new
python -m scripts.speed_normalized_experiment evaluate --output outputs/speed-normalized-v1
python -m scripts.order_tools_check --output outputs/order-tools-check-new
python -m scripts.publish_speed_summary --numeric outputs/order-tools-check-new --output outputs/speed-normalization-summary.json
```

`prepare` and `evaluate` make no model calls; `speed_context_experiment run` sends the prepared requests and needs the pinned deployment and an Entra session. The recorded screen used `outputs/difference-screen-v1` (Ottawa and UORED in one invocation, MAFAULDA in another, query limit 400, seed 20261001) and the model test `outputs/speed-context-v1`, `outputs/speed-matched-v1` and `outputs/speed-normalized-v1`; each `run` command sends that folder's prepared requests. The nearest normalized order-spectrum control was added to the normalized experiment's evaluation after its requests were registered; request construction is unchanged. Ottawa additionally needs the audited local export `data/ottawa-simulation-v1`.
