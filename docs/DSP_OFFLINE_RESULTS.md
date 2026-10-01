# Offline Multi-Reference DSP Results

**Retain the historical numerical baseline as the control; this replay does not demonstrate a diagnostically superior DSP representation.** It produced 12/12 correct forced labels with four references and with eight references. The added representations produced 9-12/12, depending on resolution and bank size. The new report makes spectral contributions, reference variability and disagreements inspectable, but calibrated acceptance/rejection and progressive human enrichment remain untested. No AI request was made.

## Forced-Label Correctness Depends On Representation And Bank

The fixed [offline protocol](DSP_OFFLINE_PROTOCOL.md) uses four front-direction seed windows, adds four left-direction windows and evaluates twelve already consumed right-direction windows. Each class has one reference per represented direction. The twelve queries share four original acquisitions; they are not twelve independent machines or sessions. Bank expansion uses four additional publisher labels and is a batch ablation, not feedback triggered by rejection.

| Representation | 4 refs: correct | 4 refs: wrong | 8 refs: correct | 8 refs: wrong | 4 refs: fully correct acquisitions | 8 refs: fully correct acquisitions |
| --- | --- | --- | --- | --- | --- | --- |
| Historical full-band baseline | 12/12 | 0/12 | 12/12 | 0/12 | 4/4 | 4/4 |
| Common band, 1,024 samples | 12/12 | 0/12 | 10/12 | 2/12 | 4/4 | 3/4 |
| Relative floor, 1,024 samples | 12/12 | 0/12 | 10/12 | 2/12 | 4/4 | 3/4 |
| Whole-window Welch, 20 ms | 12/12 | 0/12 | 9/12 | 3/12 | 4/4 | 3/4 |
| Whole-window Welch, 100 ms | 9/12 | 3/12 | 12/12 | 0/12 | 3/4 | 4/4 |
| Whole-window Welch, 500 ms | 9/12 | 3/12 | 12/12 | 0/12 | 3/4 | 4/4 |
| Temporal median, 20 ms | 12/12 | 0/12 | 9/12 | 3/12 | 4/4 | 3/4 |
| Temporal median, 100 ms | 9/12 | 3/12 | 12/12 | 0/12 | 3/4 | 4/4 |
| Temporal median, 500 ms | 9/12 | 3/12 | 12/12 | 0/12 | 3/4 | 4/4 |

Each cell has twelve query decisions. All eighteen configurations had 0/12 unavailable or tied outputs; both offline attempts completed without technical failure. These are forced candidates among known classes. There is no measured false-rejection rate, excluded-class rejection rate, wrong-acceptance rate, automatic operational coverage or human-review saving. The report's status remains `uncalibrated_review_required` with a null operational decision. The earlier [AI comparison results](DSP_LABELED_RESULTS.md), including 11/12 known labels and 2/4 excluded-class rejections, use a different decision contract and remain unchanged.

## Observations Do Not Establish The Proposed Mechanisms

The relative floor changed no aggregate correctness count compared with the matched common-band control. Temporal medians matched their corresponding whole-window Welch correctness counts at all three tested durations. These equalities do not imply identical spectra, distances or decisions on other inputs.

Adding left-direction references improved the 100/500 ms representations from 9/12 to 12/12, but reduced the common-band short-frame controls from 12/12 to 9/12 or 10/12. The closest-regime class rule can reduce a competing class's score when references are added. The measurements show that bank expansion is not monotonically beneficial; the specific physical cause of these errors has not been established. Frequency-response differences, acquisition direction, regime coverage and loss of discriminative high-frequency information remain hypotheses requiring separate controls and fresh acquisitions.

The full-band baseline already reaches the forced-label ceiling in this small replay. More references or longer frames do not improve that count, and no extra benefit from AI interpretation is demonstrated. Do not select the best-looking row as a confirmed replacement or infer reliable novelty rejection from closed-set correctness. Source exposure, four query acquisitions, unknown machine/session independence and original encoding confounds limit generalization.

## Inspect And Reproduce The Evidence

The final local artifact is `outputs/dsp-offline-jin-v2/report.html`. It displays the first fixed query against all eight references, all class/regime rankings, quality and coverage, within-class ranges and twenty-four aligned comparison figures. Each figure includes centered spectral shapes with temporal quantiles, the difference curve, additive squared-distance contributions by band and per-window query distances. The self-contained HTML opens without a server; reference sections expand independently. Source paths and query truth are excluded from the report and numerical input features.

The same directory contains hash-bound `registration.json`, `features.json`, `evidence.json`, `predictions.json`, `scores.json`, `manifest.json` and restricted `audit` provenance. The 216 recorded predictions cover twelve queries, nine representations and two bank sizes; they are repeated analyses of the same inputs, not 216 independent cases. Correctness scoring occurs after predictions are written. Per-query replay class scores beyond the displayed first query can be recomputed from the frozen inputs; the artifact retains their candidate and margin, not a full image report for every replay query. Version 1 remains preserved; version 2 adds acquisition-level counts and final implementation-hash verification without changing candidate predictions.

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_compare_offline --jin-replay outputs/dsp-jin-v1 --output outputs/dsp-offline-jin-reproduction
.\.venv\Scripts\python.exe -m pytest tests/test_dsp.py tests/test_dsp_similarity.py tests/test_dsp_packet.py -q
.\.venv\Scripts\python.exe -m ruff check src/modelmetis/dsp_comparison.py scripts/dsp_compare_offline.py tests/test_dsp.py
```

The comparison-specific synthetic checks cover physical resolution at four native rates, gain invariance, modulation sidebands, temporal changes, impulse occupancy, filter/noise sensitivity, near-full-scale flags, unavailable evidence, grouping, duplicate/source-hash rejection, baseline reconciliation and immutable reports. These establish implementation behavior only. Browser validation checks image loading, nonblank plots and layout at desktop/mobile widths; it does not validate diagnostic interpretation.

The scoped regression suite passed 36 tests and the changed Python files passed Ruff. All 34 manifest-listed files and all registered implementation hashes verified; independent recounting reconciled 216 predictions and eighteen window/acquisition score rows. Historical report-array calculations reproduced all twelve seed-baseline candidates and the four reference distances for the displayed query. All 24 PNGs were nonblank at 1,200 by 1,100 pixels and loaded at browser widths 1,440 and 390 pixels without page-level horizontal overflow. All 48 local links in the six touched documents resolved. The full repository test suite and real human enrichment were not run.

The [progressive enrichment protocol](DSP_OFFLINE_PROTOCOL.md#human-enrichment-requires-a-new-frozen-registration) remains a design deliverable. It requires a new approved registration, independent calibration roles, immutable first decisions, feedback available only after rejection, versioned reference admission and scoring on subsequent independent inputs. No sequential oracle stream, human review campaign, threshold tuning, AI experiment or promotion was executed.
