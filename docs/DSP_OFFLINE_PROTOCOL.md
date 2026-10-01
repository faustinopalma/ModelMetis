# Offline DSP Comparison And Progressive Enrichment

**Use the deterministic multi-reference report to inspect spectral evidence before authorizing further AI experiments. No representation is established as diagnostically superior, and acceptance/rejection thresholds remain uncalibrated.** The implementation separates representation ablations from reference-bank expansion, preserves the historical numerical baseline and produces forced candidate rankings without an operational diagnosis. Synthetic checks validate calculations; a fixed replay of previously consumed Jin acquisitions measures exploratory forced-label correctness. Progressive human enrichment remains a proposed protocol, not an executed experiment.

The [measured offline results](DSP_OFFLINE_RESULTS.md) are separate from this design contract: the baseline achieved 12/12 forced labels and the added representations achieved 9-12/12. These observations authorize no new inference or enrichment run.

## Representations Have Explicit Physical And Numerical Meaning

Power spectral density (PSD) is signal power per unit frequency. Welch PSD averages windowed periodograms; short-time Fourier transform (STFT) power retains individual frame estimates. Full-scale (FS) units refer to the digital waveform, not calibrated acoustic pressure. Hann equivalent noise bandwidth (ENBW) describes the effective noise bandwidth of the analysis window; it is not a claim that two tones one bin apart are resolved.

The separate [comparison module](../src/modelmetis/dsp_comparison.py) operates on an explicitly selected native channel. It reuses the integrity-checked decoder and preserves source levels. The [existing DSP pipeline](DSP_PIPELINE.md), full-report AI runner, frozen configurations and historical artifacts are unchanged. A comparison rejects duplicate decoded waveforms, duplicate IDs, conflicting acquisition-group labels and any query/reference acquisition-group overlap. Native channel selection, byte hashes and acquisition IDs belong in restricted provenance. Physical machine/session independence still depends on truthful source metadata.

| Representation | Fixed definition | Isolated comparison |
| --- | --- | --- |
| Historical baseline | Full-band Welch, 1,024 samples, 256-sample hop, periodic Hann, 10-second intervals, absolute PSD floor 1e-30; mean-centered log PSD, then interval mean | Reproduces the labeled single-channel calculation; short/low-energy input is unavailable rather than a forced silent match |
| `band_1024` | Same baseline frames, intervals and floor, restricted to 20-4,000 Hz and recentered | Measures the effect of removing frequencies outside the common band |
| `floor_1024` | Same restricted calculation, floor 80 dB below each spectrum's maximum | Measures floor choice; floor scales with linear gain |
| `welch_0.02`, `welch_0.1`, `welch_0.5` | Same band/floor and 10-second intervals; frames of 20, 100 and 500 ms, integer hop of one quarter frame | Measures physical frame duration; requested and actual duration remain explicit |
| Temporal shape, `0.02`, `0.1`, `0.5` | Same physical frames, band and relative floor inside nonoverlapping one-second windows; median centered shape across available windows | Measures the temporal-summary extension against its corresponding whole-window Welch control |

Frames use native integer sample counts, without resampling or zero padding. Defaults give bin spacing 50, 10 and 2 Hz, and Hann ENBW 75, 15 and 3 Hz. Frequency grids must agree exactly within 1e-9 Hz for temporal comparisons; incompatible rounded grids are unavailable. Baseline and whole-window ablations conservatively require equal sampling rates. The common upper frequency is a design choice, not evidence that higher-frequency fault information is irrelevant.

For each PSD vector, apply the declared floor, take 10 log10 and subtract its frequency-bin mean. Comparison distance is the root mean square difference between shape vectors. Frequency bins have uniform weight. Each band's contribution is the sum of squared differences in that band divided by the total number of bins; these contributions sum to the squared overall distance. Bands are 20-250, 250-1,000, 1,000-2,000 and 2,000-4,000 Hz, with only the final upper edge included. Distances and margins are descriptive, not probabilities.

The report retains median and 10th/90th percentile window shapes, each query-window distance to each reference median, native start/end samples, missing windows, uncovered STFT tails and floor occupancy. Frame departure above 6 dB from its window's average shape is an uncalibrated transient indicator. Only active frames above the relative energy floor enter its denominator; active and total frame counts are retained. These frame estimates overlap and the one-second windows share acquisitions. Quantiles are not confidence intervals, transient occupancy is not fault prevalence, and resolutions are correlated measurements rather than independent votes. Frame PSDs support these measurements but are not exported as new STFT image panels.

Raw RMS, DC offset, peak and samples near full scale remain acquisition-quality context. AC RMS below 1e-10 FS, insufficient frame length or comparison-band power below the squared RMS floor makes that window unavailable. Low-energy input is not evidence for a normal class. A clipped or partly unavailable recording can still have a descriptive ranking; the current API always returns `uncalibrated_review_required` and no diagnosis. Any later classifier must implement explicit quality and coverage gates before acceptance.

## Classes Retain Distinct Acquisition Regimes

A reference has an opaque ID, a class ID, a declared regime ID, an original acquisition-group ID, a source hash and an explicit channel. A regime describes known acquisition or operating context; the implementation does not discover mechanically meaningful regimes. Multiple windows from an acquisition remain dependent observations.

For each representation, compute query-to-reference distances, take their median within each acquisition, take the median across acquisitions of each regime, then select the closest regime for each class. Report every regime, not just the winner. Rank classes by that score and report the closest competitor and its score minus the winning score. Exact score ties have no forced candidate. Any unavailable reference blocks a complete class ranking for that representation. This conservative completeness rule is not a calibrated rejection rule.

The report exposes reference/acquisition counts, within-regime and cross-regime reference-distance ranges, and cross-acquisition pair counts. A singleton has unmeasured variability, not zero variability. Pairs sharing a reference are also dependent. Repeating an identical feature window from the same acquisition cannot increase that acquisition's vote. Unequal regime/acquisition counts are flagged: median aggregation does not eliminate the advantage of searching more regimes or all sample-selection bias. Future comparisons must use equal labeled budgets, fixed per-class/per-regime caps and an acquisition-balanced subsampling control. Do not discard rare legitimate regimes merely to make a centroid compact.

## Offline Validation Separates Arithmetic From Diagnostic Correctness

| Check | Required observation | Claim it cannot establish |
| --- | --- | --- |
| Linear gain within available, unclipped range | Shape distance approximately zero; RMS changes by the known gain | Robustness to microphone response, placement or load |
| Known 1,000/1,040 Hz tones at 8/16/42/44.1 kHz | Fine representation retains both peaks and declared bin spacing/ENBW | Resolution of arbitrary noisy field recordings |
| 2,000 Hz carrier modulated at 40 Hz | Sidebands at 1,960 and 2,040 Hz | Mechanical cause or shaft speed |
| Known transition, impulse, silence and short tail | Temporal variation/occupancy visible; unavailable input and sample coverage explicit | Validated regime segmentation or fault detection |
| Low-pass filter, added noise and clipping | Shape sensitivity retained; near-full-scale quality indicator changes | Successful transfer across real acquisition chains |
| Reference groups, duplicate inputs, source mutation and overwrite | Unsafe or inconsistent input fails; attempts and immutable output remain inspectable | OS-enforced data isolation or authentic human review |
| Baseline and band-control reconciliation | New calculations agree with the existing DSP arrays | New diagnostic accuracy |

The [test implementation](../tests/test_dsp.py) contains these synthetic and report-integrity checks. The baseline/band/floor/duration/temporal chain changes one representation stage at a time. A stage can contain coupled operations, particularly one-second segmentation plus median temporal summary; its contribution cannot be attributed to the median alone. The expanded-bank comparison repeats the entire chain, so improvements from extra labeled examples are not attributed to DSP alone.

The fixed Jin replay uses four front-direction 0-second seed windows, four left-direction 0-second additions and twelve right-direction query windows at 0, 120 and 240 seconds. M01 and M02 mean front and left acquisition directions, respectively. Allocation follows existing roles and offsets, without outcome-based selection. Seed and expanded banks consume four and eight publisher-labeled references; this is a batch reference-budget ablation, not simulated human arrival. The twelve queries share four original acquisitions; unit/session identities are unknown and all sources have previous project exposure. No fresh confirmation claim or configuration selection follows these results.

Registration binds source specifications, code hashes, runtime versions and representation settings before computation. Comparison functions receive no query labels; forced predictions are serialized before evaluator scoring. The replay adapter reads historical truth to map the four already labeled additions and their offsets; this local separation is a software boundary, not a sealed process. Scoring reports correct forced labels, wrong forced labels and unavailable/tied outputs separately, each against the query denominator. Known recognition with rejection, excluded-class rejection, wrong acceptance and human effort remain unmeasured. No inference endpoint, credentials or paid-call runner is used.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dsp.py -q
.\.venv\Scripts\python.exe -m scripts.dsp_compare_offline --jin-replay outputs/dsp-jin-v1 --output outputs/dsp-offline-jin-v2
```

Use a new output directory for every attempt. The offline generator writes a self-contained `report.html` for the first fixed query and expanded bank, all numerical features for that report, its evidence JSON, aligned PNGs, registration, restricted provenance and a file-hash manifest. `predictions.json` and `scores.json` cover all twelve queries and both bank sizes. Correctness scoring is separate from the label-free per-query report.

For another fixed input, use `--spec` with a local JSON object containing `schema: 1`, `references` and `query`. Each reference requires `id`, `class_id`, `regime_id`, `group_id`, `wav`, `audio_sha256` and zero-based `channel`; the query uses the same fields except class/regime IDs. Paths resolve relative to the specification. IDs use R/Q/D/T plus digits for recordings, C plus digits for classes and M plus digits for regimes. Additional fields are rejected. Input labels and source paths stay outside the public comparison evidence. Generic reports do not score query truth.

## Human Enrichment Requires A New Frozen Registration

The operational hypothesis is that occasional verified exceptions can improve subsequent automatic coverage without increasing accepted-label error. A separate simulation may use publisher truth as a disclosed oracle with origin `simulated_human_from_publisher`; this is not an actual human diagnosis or a measure of human annotation time. The current labeled review page exposes truth immediately and cannot implement blind first decisions or this sequential protocol.

1. **Freeze groups and roles before segmentation.** Define seed references, development/calibration, enrichment stream and sealed evaluation acquisitions. Keep duplicates, channels, paired microphones and augmentations together. Record physical units/sessions when known and acknowledge residual confounds when unknown. Previously consumed acquisitions support development/replay only.
2. **Freeze representation and decision policy.** Register numerical-only baseline, each retained DSP ablation, reference aggregation, quality/coverage gates, distance-radius and competing-margin selection procedure, random seeds, stream order, budget, stopping rules and optional later AI comparator. Calibrate only on designated development groups. Existing Jin thresholds do not transfer automatically to a new representation or bank. A novel-class test must remove that class from both references and calibration.
3. **Record the first decision against bank version v.** Append sample/group hash, bank and taxonomy hashes, all evidence, model/configuration hash if applicable, result and failure state before querying the oracle. Use `known(class_id)`, `different`, `ambiguous` or `unusable`; technical failures have no semantic decision. `different` means outside the registered support evidence, not a physical fault diagnosis.
4. **Reveal only eligible feedback.** A recorded `different` triggers investigation. The reviewer can confirm an existing class, establish a new class with supporting evidence, or leave the case unresolved. `unusable`, technical failure or ambiguity can trigger a separately counted quality/review workflow; they cannot silently create a new class. Accepted cases stay unrevealed to the learner. The sealed evaluator may score them without passing per-example errors back into selection.
5. **Commit an explicit bank transaction.** Retain the original decision unchanged. A confirmed, usable addition creates bank v+1 with parent hash, reviewer/oracle origin, label, acquisition group, evidence, taxonomy revision and admission/removal reason. Enforce duplicate checks and registered size caps; preserve rare regimes under a declared policy. Do not admit evaluation data, automatic predictions or model agreement as gold. Stop before an addition that exceeds the label or storage budget.
6. **Measure only subsequent independent inputs.** An added example cannot improve its own original score. Quarantine remaining windows of that acquisition from independent future scoring, or report them separately as same-acquisition reuse. Periodic evaluation uses a read-only bank snapshot; evaluation results cannot trigger additions or hyperparameter changes. Rollback preserves the attempted version and its evidence.
7. **Compare matched-cost streams.** Run frozen seed-only and enrichment policies on the same preregistered order, and include a reference-count-matched fixed selection control. An optional AI interpreter sees exactly the same permitted evidence as the numerical rule. Count every supplied label, rejected/unresolved review, retried technical attempt and bank replacement. Select neither stream order nor checkpoints from evaluation outcomes.

### Ottawa Needs A Separate Calibration Allocation

The earlier 8-seed / 104-stream / 16-evaluation proposal leaves no disjoint calibration set. If thresholds are fitted using Ottawa, the proposed allocation becomes eight profile-1 unloaded seed acquisitions, sixteen profile-2 acquisitions for development/calibration, eighty-eight stream acquisitions (eight profile-1 loaded plus eighty from profiles 3-7), and sixteen profile-8 evaluation acquisitions. This accounts for all 128 without reusing calibration as stream evidence. Two calibration acquisitions per class cannot establish reliable class-tail quantiles. Motor/class confounding and previous project exposure remain; a confirmatory claim requires fresh groups.

Stream order must be hash-bound and independent of hidden labels. Record source chronology when available; a deterministic shuffled replay is simulated order, not observed temporal operation. A proposed exploratory budget is at most 24 stream oracle interventions, yielding at most 32 bank references if every intervention confirms one admissible example. Count the eight seed labels and sixteen calibration labels separately: the maximum label budget is 48, not 24. Unresolved interventions still consume budget. This is a proposal requiring approval and registration; no stream or enrichment has been run.

### Score Errors, Coverage And Human Cost Together

| Metric | Numerator / denominator | Required qualification |
| --- | --- | --- |
| Correct automatic known decision | Correct accepted known labels / all known inputs | Rejections and technical failures stay in the denominator |
| Wrong known assignment | Accepted wrong known labels / all known inputs | Rejection-only feedback will not repair these directly |
| False rejection | `different` on known inputs / all known inputs | Keep ambiguity, unusable input and technical failures separate |
| Correct excluded-class rejection | `different` on excluded-class inputs / all excluded-class inputs | Reference removal is not genuine unseen-fault validation |
| Wrong acceptance | Accepted known label on excluded-class input / all excluded-class inputs | Also contributes to accepted-label error |
| Accepted-label error | Wrong accepted decisions / all accepted decisions | Undefined when no decisions are accepted |
| Automatic coverage | Accepted decisions / all submitted inputs | Report technical completion separately |
| Human load | Oracle/reviewer interventions / stream inputs, plus absolute label counts | Seed, calibration, stream, optional audit and unresolved reviews remain separate |
| Bank growth | References, acquisition groups, regimes and classes per version | Windows are not independent labeled acquisitions |
| Subsequent improvement | Paired changes from the frozen-bank control on later inputs | Separate same-acquisition reuse and report fixed evaluation snapshots |

Report both window-level counts and acquisition-level outcomes, including whether all windows in a group were correct. If uncertainty is estimated, resample acquisition groups rather than correlated windows and disclose the small number of groups. Four Jin query acquisitions or sixteen Ottawa evaluation acquisitions cannot substantiate a low population error bound. Before any new AI campaign, agree on minimum recognition, maximum accepted-label error, minimum coverage, maximum human budget and an evaluation size that can support those claims; leave deployment promotion blocked until then. Synthetic correctness, a completed report or an LLM explanation satisfies none of these diagnostic gates.
