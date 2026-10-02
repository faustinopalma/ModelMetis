# Difference From The Same-Regime Normal: Study Protocol

**Status: not pursued. The [deterministic screen](DIFFERENCE_SCREEN.md) found that the difference matches raw spectra within one regime and loses under speed changes, while stating the shaft speed helps.** The design below is kept as the record of what was considered.

**Proposed primary definition: the difference Δ is the per-frequency log-power ratio, in dB, between a sample and the healthy normal recorded in the same regime, expressed in units of the normal's own variability; a sample is attributed to the class whose Δ it matches, or the system abstains.** The difference changes decisions only when sample and class references come from different regimes: within one regime, the plain Δ distance equals the raw-spectrum distance algebraically. The study therefore tests one claim: subtracting a same-regime healthy recording removes regime effects that defeat raw spectra across Ottawa profiles and Jin microphone directions. Status: design awaiting approval. Nothing below has been measured on evaluation cases, and no model call, training or Azure operation is part of this protocol.

If the claim holds, reference collection becomes cheaper: one healthy recording per operating regime, instead of every fault class in every regime. If it fails, the failure must be attributed to a measured cause: speed-dependent fault frequencies, machine identity or acquisition artifacts.

## The Difference Matters Only Across Regimes

Let L(f) be a recording's log-power spectrum in dB, N_q the normal of the query's regime and N_k the normal of class k's reference regime. Then Δ_q = L_q − N_q, Δ_k = L_k − N_k and Δ_q − Δ_k = (L_q − L_k) − (N_q − N_k). Without tolerance weighting, the Δ distance is the raw distance corrected by the healthy machine's own change between the two regimes.

- **Same regime (N_q = N_k).** The plain Δ distance equals the raw distance; nothing changes. Δ adds value only through the healthy anchor (Δ ≈ 0 means healthy), variability weighting and significance masking.
- **Regime change acting as a filter.** Gain, microphone response, position and acoustic path multiply the power spectrum and add a constant per-frequency offset in dB. If the same offset applies to the healthy and the faulty machine, it cancels exactly.
- **Regime change moving frequencies.** A speed change moves shaft-locked lines. Subtracting the healthy normal removes the healthy lines at the new speed, but a fault line that also moves with speed does not land where the reference Δ placed it. Fixed-frequency content cancels; speed-locked fault content requires tolerance to small shifts or an order axis.
- **Different machines.** If the normal and the sample come from different machines, Δ contains the machine difference as well as the fault. Δ cannot separate the two without repeated faults across units.

## Definitions

### Normal State

The normal of a regime is a healthy recording of the same machine in the same regime: identical microphone position, acquisition chain, speed profile and load. It is summarized by the mean log-power μ_N(f) over one-second sub-windows and their dispersion σ_N(f). The recording must never contribute a window to class references or tests. When the normal comes from another machine or another regime, the result is reported in a separate, declared arm.

Three normal models were considered:

| Model | Content | Advantage | Limit | Status |
| --- | --- | --- | --- | --- |
| N1, single point | μ_N only, fixed tolerance σ0 | Needs one short recording | Cannot distinguish a real shift from normal fluctuation | Secondary |
| N2, within-recording dispersion | μ_N and σ_N from one-second sub-windows, floor σ0 | Available in both datasets with one definition; weights unstable bands down | Underestimates session-to-session variability | **Primary** |
| N3, several healthy acquisitions | Between-acquisition dispersion | Measures the variability that matters | Not available within one regime in Jin or Ottawa | Unavailable; only mismatched regimes provide it |

The tolerance is s(f) = sqrt(σ_N(f)² + σ_x(f)² + σ0²), where σ_x is the sample's own sub-window dispersion and σ0 = 1 dB. The floor prevents near-stationary bins from dominating with near-zero dispersion; it is the order of the 0.70 dB median distance between windows of one Jin acquisition reported in [family separation](DSP_FAMILY_SEPARATION.md). Sensitivity is reported for σ0 = 0.5 and 2 dB.

### Difference And Significance

Δ_x(f) = L_x(f) − μ_N(f), where L_x is the mean of the sample's one-second log-power spectra. A bin is significant when |Δ_x(f)| / s(f) > 3. The detection statistic D_x is the fraction of significant bins. Primary Δ is mean-centered over frequency, matching the historical gain-centered baseline, because the recording gain is not known on a common scale: Jin healthy and fault files use different encodings, and Ottawa exports are peak-normalized. An absolute-level arm restores Ottawa microphone volts from the audited peak values and is reported separately.

### Comparison

The primary comparison is the tolerance-weighted distance d(x, k) = sqrt(mean_f (Δ_x(f) − Δ_k(f))² / (s_x(f)² + s_k(f)²)). When both differences match up to normal variability, d is close to 1. The healthy class enters as the zero curve Δ_H ≡ 0 with the tolerance of its normal, so healthy is a candidate like any fault.

| Metric | What it compares | Advantage | Limit | Status |
| --- | --- | --- | --- | --- |
| Tolerance-weighted RMS distance | Whole Δ curves, including magnitude | Reduces to the historical baseline when weighting and normal are removed; enables a clean ablation | Severity changes magnitude and distance | **Primary** |
| Plain RMS distance in dB | Whole Δ curves | Identical algebra to the baseline correction | Ignores which bands are unstable | Secondary |
| Cosine over the union of significant bins | Shape and sign where either Δ departs from normal | Insensitive to fault severity | Undefined when nothing is significant; unstable with few bins | Secondary |
| Sign-localization overlap | Jaccard overlap of significant positive and negative bin sets | Directly readable as "same bands up or down" | Discards magnitude; sensitive to the threshold | Descriptive |
| Overall magnitude | RMS of Δ / s | Separates healthy from faulty | Does not identify the class | Used only in detection |

### Decision And Abstention

1. **Forced recognition.** The nearest class under d, including healthy, is the label. This measures separability without any threshold.
2. **Recognition with abstention.** Accept the nearest class k* only if d(x, k*) ≤ a and d(x, k*) ≤ ρ · d(x, second nearest). Otherwise answer `different`. Healthy is accepted as k* like any other class, so "Δ within normal variability" and "Δ significant but unlike every class" are the two outcomes the rule separates.
3. **Calibration.** a and ρ come from the grid a ∈ {1.5, 2, 3, 4, 6} and ρ ∈ {1.0, 0.8, 0.67}, chosen on development cases only by maximizing correct known plus correct excluded decisions; ties choose the smallest a, then the smallest ρ. The raw-spectrum ablation is calibrated with the identical grid and rule.

The detection threshold τ_H on D_x is fixed at 0.05 before real-data evaluation, with sensitivity at 0.02 and 0.10. In both datasets the only same-regime healthy acquisition is the normal itself, so in-regime healthy detection cannot be tested on real data; τ_H is exercised in the synthetic study and the mismatched-normal arm.

## Representations

The waveform cannot be subtracted: recordings are not phase-aligned, and two healthy recordings of one machine differ sample by sample. Every candidate below is phase-free and turns a multiplicative change into an additive one, or is explicitly normalized.

| Representation | Physical reading | What subtraction cancels | What it cannot cancel | Status |
| --- | --- | --- | --- | --- |
| R1, Welch log-PSD, 1,024-sample Hann frames, hop 256, native grid | Average spectral shape, tones, resonances | Gain, microphone and path response shared by sample and normal | Speed-moved lines, machine identity | **Primary**, matches the historical baseline frames |
| R1s, R1 smoothed to 1/6 octave | Same, at coarse resolution | As R1 | Large speed shifts | Secondary: tolerance to small speed shifts |
| R2, R1 with the smooth spectral envelope removed by liftering below 1 ms quefrency | Fine structure: harmonics, sidebands, narrow lines | Smooth transfer functions that differ between normal and sample, for example position | Fine-structure artifacts, speed shifts | Secondary: position tolerance. Covers the cepstrum, because the cepstrum is a linear transform of the log spectrum and its Δ is the transform of R1's Δ |
| R3, envelope spectra in the five [extension](DSP_EXTENSIONS.md) carrier bands, 100 Hz to 16 kHz, divided by the mean envelope | Modulation and periodic impacts | Carrier gain | Speed-locked modulation frequencies | Secondary: bearing and impact faults |
| R4, per-frequency 10/50/90% quantiles of short-frame log-PSD | Intermittency: how often a band rises | Gain, path response | Event timing is deliberately discarded | Secondary |
| R5, relative band powers in dB | Coarse energy allocation | Gain | Most fine structure | Control: coarse representation, poor in the family study |

Order normalization would cancel speed-locked shifts. Neither dataset supplies a measured shaft speed, but Ottawa's constant profiles declare the drive frequency; slip makes shaft speed slightly lower. It stays out of the primary study; an exploratory variant rescales constant-profile frequencies by the declared drive frequency, never by anything derived from the sample's label.

## Data Allocation

Whole acquisitions keep one role. Windows of one recording are dependent and are reported with their acquisition. Every dataset in this study was used in earlier development, so no result is a clean evaluation.

### Jin: Front References, Left Development, Right Test

The design mirrors the historical comparison so the same right-microphone windows can be scored. Each direction has one healthy recording; it becomes that direction's normal. Healthy windows inside a normal cannot also be tested against it.

| Role | Front | Left | Right |
| --- | --- | --- | --- |
| Normal | `nf10m.wav`, whole recording | `nl10m.wav`, whole recording | `nr10m.wav`, whole recording |
| Class references | Fault windows at 0 s from `b1f`, `b2f`, `b3f` (historical R03, R01, R04); healthy is Δ ≡ 0 | None | None |
| Development, calibrates a and ρ | None | D01, D02, D05, D06, D07, D08: six fault windows at 0 and 120 s | None |
| Test | None | None | T01-T03, T07-T12: nine fault windows at 0, 120 and 240 s |
| Not evaluable within the regime | None | D03, D04, inside the left normal | T04-T06, inside the right normal |

Excluded-class tests remove the query's own class reference and expect `different`: the historical three (T01, T07, T10) and, separately, all nine fault windows. Rejected alternatives: splitting a healthy recording in time into normal and test creates artificial independence; leaving healthy windows inside their own normal makes Δ trivially zero.

The **mismatched-normal arm** keeps all twelve right windows, including T04-T06, by using the left normal for right queries. It measures what the direction change leaves in Δ and is never pooled with the primary arm. A **rotation arm** repeats the design with each direction as test and the other two as class references, giving class Δ references from two regimes; it is descriptive.

### Ottawa: Profile 1 References, Other Development Profiles, Profile 2 Test

Each operating cell, a speed profile and a load, has one healthy acquisition `H_H_p_l`; it is the normal of that cell. Class Δ references use the historical profile-1 unloaded fault acquisitions with `H_H_1_0` as their normal. Profiles 5 and 7 are never decoded.

| Role | Cells | Acquisitions |
| --- | --- | --- |
| Normal | `H_H_p_l` of every used cell | One per cell |
| Class references | Profile 1, load 0, seven faults | 7 |
| Development, calibrates a and ρ | Profiles 3, 4, 6 and 8, both loads, seven faults | 56 |
| Test, historical case set | Profile 2, both loads, seven faults | 14 |
| Not evaluable within the regime | `H_H_2_0`, `H_H_2_1`: they are the normals | 2 |
| Locked | Profiles 5 and 7, both loads, all classes | 32, never decoded |

Excluded-class tests use the same 14 test and 56 development acquisitions. The **mismatched-normal arm** uses the other load's healthy acquisition of the same profile, which admits all 16 historical profile-2 cases, including healthy. A **transfer matrix** over all unlocked cells, references from one cell and queries from another, reports forced recognition by profile and load change; it is descriptive.

## What The Difference Cannot Cancel

**Ottawa machine identity.** The publisher describes eight motors for eight conditions, and the audit could not exclude that each condition is a separate motor. In that case Δ_k contains the fault plus the difference between that motor and the healthy motor; the two cannot be separated in this dataset, and a stable Δ across profiles may be motor identity. The study reports, per class, the regime stability of Δ beside raw spectra and splits Δ into its smooth envelope and fine structure (R1 versus R2). The split describes where Δ lives; it does not attribute Δ to the fault. No Ottawa result may be described as fault recognition independent of the motor.

**Jin acquisition chain.** Preliminary checks on the first ten seconds of each raw file show more than a container difference. The three healthy files are PCM16 with 237-478 distinct sample values; the nine fault files are FLOAT with 27,721-438,775 distinct values. Median 18-21 kHz power is 5-16 dB higher in each direction's healthy file than in its fault files. Every fault Δ in Jin therefore contains a shared healthy-chain component. It does not distinguish fault classes from each other, but it can make every fault look significant and can inflate shape similarity between fault Δs. The study reports the primary full band and a declared encoding-guard arm restricted to 20 Hz-15 kHz. Unit and session identity of the Jin motors remain undocumented.

**Position and microphone.** Δ cancels them only when normal and sample share them. The mismatched-normal arms measure the residue directly.

**Speed and non-stationary regimes.** The publisher defines the Ottawa profiles as drive frequencies: 1-4 constant at 15, 30, 45 and 60 Hz; 5 and 6 increasing from 15 to 45 Hz and from 30 to 60 Hz; 7 and 8 decreasing from 45 to 15 Hz and from 60 to 30 Hz. The historical test therefore compares 30 Hz queries with 15 Hz references, and development profiles 6 and 8 are ramps. Long-term averaging smears ramps in both sample and normal. Results are reported by profile.

## Controls

| Control | Purpose |
| --- | --- |
| Raw ablation: identical pipeline with μ_N := 0, same references, cases, rule and calibration grid | Isolates the effect of subtracting the normal |
| Historical baseline recomputed from the existing Welch distance: Jin reserved 12/12, Ottawa profile 2 2/16 | Confirms the new pipeline starts from the recorded numbers; historical model results remain separate references |
| Mismatched normal: other direction or other load | Measures what a wrong normal leaves in Δ; admits healthy cases |
| Wrong anchor, Ottawa: each fault class in turn replaces healthy as the normal, and that class leaves the candidate set for that run | Tests whether healthy matters or any same-regime anchor corrects the regime |
| Encoding guard, Jin: 20 Hz-15 kHz | Measures the influence of the healthy-chain component |
| Label permutation, fixed seed | Chance level for each denominator |

External published scores remain declared references in [benchmark status](DSP_BENCHMARK_STATUS.md), never direct comparisons.

## Phase 2: Synthetic Verification

Deterministic fixtures check that Δ behaves as the algebra predicts before real data is read. The base healthy signal contains shaft harmonics, a fixed electrical line, a structural resonance and colored noise, with fixed seeds.

| Element | Variants |
| --- | --- |
| Injected faults | Shaft-order tone; sidebands at ±shaft frequency around a carrier; amplitude modulation of a resonance; periodic impulses exciting a high resonance; an unseen fixed-frequency tone held out for abstention |
| Regime changes | Gain ±12 dB; position filter with tilt and resonance; speed shift of 2% and 8% |
| Machine change | A second base signal with a different resonance and harmonic profile |

Tests must show:

1. Gain and filter changes: Δ recovers the fault class across regimes, while the raw ablation fails under the filter change.
2. Healthy with its own normal falls within τ_H; healthy with a mismatched normal exceeds it.
3. The unseen fault produces significant Δ and an abstention.
4. Speed shift: R1 degrades for shaft-locked faults; R1s recovers the 2% shift; the 8% case documents the limit; the fixed-frequency fault transfers.
5. A normal from another machine leaves a significant Δ in healthy samples: machine identity is not cancelled.
6. With identical normals and no tolerance weighting, the Δ distance equals the raw distance to numerical precision.
7. Permuted labels give chance-level recognition.

## Phase 3: Offline Evaluation On Real Data

Report each dataset, arm and representation separately; never combine the best numbers of different arms. For each decision record the query acquisition, expected class, outcome and distances. Report forced recognition, recognition with abstention and excluded-class tests with denominators and acquisition counts. Report error directions separately: wrong class, false rejection and wrong acceptance. List every case where Δ is worse than the raw ablation, with its distances.

The primary arm (R1, N2, tolerance-weighted distance, centered dB, primary allocation) is fixed by this document before any evaluation case is computed. All other arms are descriptive and cannot replace the primary result after inspection.

## Phase 4 Gate

Propose a model report only if the primary arm shows a measured advantage on the test sets: Ottawa forced recognition at least 3 of 14 fault acquisitions above the raw ablation; Jin not below the raw ablation; and, under the abstention rule, unsafe errors (wrong class plus wrong acceptance) not higher than the ablation in either dataset. A paired exact McNemar test is reported descriptively. Any model campaign requires separate approval with a registered budget.

## Implementation Boundaries

New code lives in `src/modelmetis/dsp_difference.py`, `scripts/dsp_difference_study.py` and `tests/test_dsp_difference.py`; outputs go to a new `outputs/dsp-difference-v1` that refuses to overwrite. The study registers code, protocol and source-audio hashes before computing. Registered code, frozen protocols and historical outputs remain unchanged. Ottawa profiles 5 and 7 are excluded from inventory before any decoding.
