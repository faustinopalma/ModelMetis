# Diagram Attribution Improves Rejection Direction, Not Recognition

**Explicitly reviewing every diagram and assessing the references first eliminated the two wrong assignments in this selected eight-decision replay, but did not improve overall correctness: 5/8 decisions remain correct.** Correct recognition with the true reference present fell from 2/4 to 1/4, while correct rejection with that reference excluded rose from 3/4 to 4/4. All six Ottawa decisions became Other, including three false rejections. This supports greater caution on these cases, not diagnostic generalization or a production reliability claim.

The model most often names band power, FFT, autocorrelation and the dominant-frequency track as decisive. It frequently relies on the supplied numerical measurements rather than image pixels. These are self-reported evidence preferences, not measured causal importance or predictive accuracy. The four query recordings were selected using their previously observed outcomes, and each was tested twice; the eight decisions are neither independent recordings nor a representative accuracy sample.

The separate [within-family separation analysis](DSP_FAMILY_SEPARATION.md) directly tests whether these representations remain stable across recordings. It supports full spectral shape and cepstrum for the observed Jin families, while Ottawa band power and dominant-frequency tracking vary more within a class than between its closest competitors. This numerical finding qualifies the reported attribution: a diagram can reveal a real regime difference without being a reliable fault-family discriminator.

## Wrong Assignments Become Review-Directed Errors

Other is the UI name for the structured `different` response with no selected class. With the correct reference present, Other is a false rejection; with that reference excluded, Other is correct. It would trigger the proposed human-review route, but human intervention was not executed.

| Measured outcome | Existing protocol | Staged diagram audit |
| --- | --- | --- |
| Correct decisions | 5/8 | 5/8 |
| Unacceptable wrong assignments | 2/8 | 0/8 |
| Correct known-class recognition | 2/4 | 1/4 |
| Wrong known-class assignment | 1/4 | 0/4 |
| False rejection with class present | 1/4 | 3/4 |
| Correct rejection with class excluded | 3/4 | 4/4 |
| Wrong acceptance with class excluded | 1/4 | 0/4 |

| Input and reference availability | Required response | Existing response | Audited response | Interpretation |
| --- | --- | --- | --- | --- |
| Jin T01, class present | C01, excess hall adhesive | C01 | C01 | Correct recognition retained |
| Jin T01, class excluded | Other | Other | Other | Correct rejection retained |
| Ottawa D01, class present | C01, healthy | C01 | Other | Correct recognition becomes false rejection |
| Ottawa D01, class excluded | Other | Other | Other | Correct rejection retained |
| Ottawa D03, class present | C02, rotor unbalance | C06, bowed rotor | Other | Wrong assignment becomes false rejection; acceptable direction |
| Ottawa D03, class excluded | Other | C06, bowed rotor | Other | Wrong acceptance becomes correct rejection |
| Ottawa D07, class present | C04, stator winding | Other | Other | False rejection remains |
| Ottawa D07, class excluded | Other | Other | Other | Correct rejection retained |

Only one of eight audited decisions assigns a class, and that assignment is correct. The absence of wrong assignments therefore accompanies very low automatic acceptance; it does not establish a useful classifier. The full twenty-four-decision campaign and the v14 interface (local source: `outputs/audio-comparison-v14/index.html`) remain unchanged.

## Initial Separability Does Not Establish Query Predictiveness

Six reference-only surveys examine the distinct reference banks before their associated queries are supplied. Each survey must cover all 26 diagram types, report observable differences, assign a provisional priority and select at most five informative types. The full Ottawa-bank survey is reused unchanged for all three known-class queries. Excluded-class cases use their corresponding reduced bank. Neither query figures nor query distances enter these preliminary surveys.

Eight subsequent classification requests receive the frozen relevant survey plus the original reference/query figures, numerical measurements and distance controls. Every request explicitly requires examination of all 26 diagram types, a per-type finding with reference/query citations, decisive diagrams, contrary evidence and changed priorities. No correct query label, prior answer or prior correctness is supplied to the model. The response order lists the diagram review before the final decision.

| Diagram type | Named in preliminary top five, out of 6 banks | Named decisive, out of 8 decisions | What the responses support |
| --- | --- | --- | --- |
| Band power | 6/6 | 8/8 | Broad energy allocation consistently influences the reported judgments |
| FFT | 6/6 | 7/8 | Resolved dominant lines and secondary families influence reported matching or rejection |
| Filter-bank kurtosis | 6/6 | 2/8 | Initially separates references, but remains decisive only in Jin |
| Autocorrelation | 3/6 | 6/8 | Influences all Ottawa decisions, which all reject |
| Dominant-frequency track | 0/6 | 6/8 | Rises after the Ottawa queries expose a different dominant frequency |
| 4-8 kHz carrier envelope | 3/6 | 3/8 | Supplies additional Ottawa modulation differences |
| 500-1,500 Hz carrier envelope | 2/6 | 2/8 | Supports the two Jin decisions |
| Spectral kurtosis | 3/6 | 1/8 | A specific Ottawa input peak matters more than generic initial priority |
| Welch PSD | 0/6 | 2/8 | Helps describe the healthy Ottawa query's shifted spectral distribution |

These counts are mentions, not accuracy scores. Related banks share most references, paired queries share one recording, and transforms of one signal are correlated. Physical STFT, wavelet and the 1,500-4,000 Hz envelope are each decisive once. Cepstrum, cyclic coherence, reassigned STFT, persistence, PSD-estimator comparison, harmonic spacing and modulation map never appear in the final decisive lists. That absence does not demonstrate that removing them preserves behavior. Orders and synchronous averaging are explicitly unavailable without an independent RPM trace.

## Three Explanations Are Supported By The Evidence

**Jin T01 has a coherent partial match, including cross-band modulation.** Its accepted class remains C01. The model cites a broad low/mid-frequency spectrum, approximately 3.5 Hz modulation in multiple carrier envelopes and concentrated low/mid-band impulsiveness. Source evidence confirms the 500-1,500 Hz envelope peak at 3.47 Hz in R01 and 3.57 Hz in T01, and filter-bank kurtosis maxima of 8.73 and 18.77. The response also acknowledges a conflicting approximately 940 Hz dominant track in T01 versus a 16 kHz median in R01. When R01 is withheld, the model rejects rather than assigning the forced nearest alternative. This is one successful paired case, not proof of fault-specific modulation.

**Ottawa D01 demonstrates how real feature differences can still produce a wrong decision.** The model rejects the healthy input using correct numerical observations: below-100 Hz power falls from 68.27% in healthy reference R01 to 39.06% in D01; 100-500 Hz power rises from 26.65% to 48.22%; spectral centroid rises from 212.52 Hz to 369.76 Hz; dominant FFT peaks shift from 45.9 Hz to 92.0/109.8 Hz. It explicitly says the decision is driven primarily by numeric observations rather than pixel estimates. The publisher label remains healthy, so accurate feature reading is insufficient for class recognition.

**Ottawa D03 and D07 expose sensitivity to operating-profile differences.** All references use profile 1, while the selected queries use profile 2, with load zero in both groups. The D03 dominant-frequency track is 90 Hz throughout, versus 40-50 Hz for its true reference R02. D07 is also fixed at 90 Hz, versus 40-80 Hz in true reference R04; its spectral-kurtosis maximum is 3.043 near 1,060 Hz. Those observations are confirmed by the deterministic evidence. The model uses them to reject even with the correct class represented. A doubled dominant component does not establish doubled rotational speed: harmonic dominance can change, and no independent RPM trace is supplied. The supported interpretation is sensitivity to acoustic regime and representation of within-class variability, not a demonstrated causal explanation of each error.

## The Responses Do Not Establish Image-Only Reasoning

The preliminary Ottawa survey states, "Numeric summaries were preferred over pixels." Ottawa D01 states, "The decision is driven primarily by observable numeric evidence rather than pixel estimates." Other responses distinguish supplied physical measurements from numerical nearest-reference controls, often rejecting despite those controls selecting a nearest class. These are three different evidence sources: image pixels, numerical DSP measurements and computed reference distances. The experiment exposes all three and cannot isolate their contributions.

All fourteen responses contain 26 diagram-review entries: 156 preliminary entries and 208 decision entries. Validated citations establish that the named evidence exists and includes the required diagram for reference and query where applicable. They do not establish that every image was visually inspected, that every written observation is correct, or that the stated rationale faithfully describes the model's internal decision process. The quantitative examples above were separately checked; the full set of 364 observations has not received an independent semantic audit.

## Prioritize Pruning From Error-Associated Attribution

Use the elicited attribution to prioritize removal of inputs named as decisive in wrong decisions. Error-associated citations are a practical intervention shortlist; causal harm is tested by removing the cited evidence and comparing matched decisions. The [completed crossed experiment](DSP_PRUNING_RESULTS.md) keeps the reference bank fixed: single removals do not recover D03/D07, and triple removal helps D01 but introduces an unsafe D03 assignment in an exact-request repeat. Overall mention frequency is neither a retention criterion nor sufficient evidence for deletion.

| Decisive diagram | False rejections / 3 | Correct known decisions / 1 | Correct excluded rejections / 4 | Pruning priority on these cases |
| --- | --- | --- | --- | --- |
| Dominant-frequency track | 3/3 | 0/1 | 3/4 | First, supported by poor cross-regime family stability |
| Autocorrelation | 3/3 | 0/1 | 3/4 | First, especially for Ottawa |
| Band power | 3/3 | 1/1 | 4/4 | Early Ottawa ablation; retain the distinction from its successful Jin use |
| FFT | 3/3 | 1/1 | 3/4 | Subsequent ablation; full spectral shape also has positive Jin evidence |
| Spectral kurtosis | 1/3 | 0/1 | 0/4 | Targeted D07 ablation; only one decisive mention |
| 4-8 kHz carrier envelope | 1/3 | 0/1 | 2/4 | Secondary candidate |
| Welch PSD | 1/3 | 0/1 | 1/4 | Secondary candidate; distinguish diagram evidence from distance controls |

All three audited errors are false rejections; this audit contains no wrong class assignment. The original paired baseline had two unacceptable assignments. Preserve the user's error hierarchy: first avoid wrong assignments, then reduce unnecessary review. A removed view may also have supported correct rejection, so a reduction in false rejections is insufficient if wrong acceptances return.

Prune the complete evidence channel for each candidate: image panels, corresponding numerical summaries and per-view distance controls. Otherwise the model can continue using the removed diagram's content through text. Use a fixed review/decision protocol, model settings and output allowance across a matched control, individual removals and a combined removal; do not compare a newly changed schema directly with historical results as an isolated pruning effect. Keep all original raw evidence and decisions immutable. Reference-bank expansion remains a separate factor. The crossed pruning trials are development evidence; no definitive pruning policy, clean final test or progressive human enrichment has been executed.

## Scope, Integrity And Reproduction

The [registration](../examples/results/diagram-audit-registration.json) records the deterministic selection: first lexical Jin correct known-class case, and first lexical Ottawa correct, wrong-class and false-rejection cases, each paired with reference removal. The [evaluation](../examples/results/diagram-audit.json) contains all validated results, survey outputs, decisive-diagram lists and paired comparisons. Per-case folders retain exact requests, raw responses, receipts and survey-to-decision hash bindings. The underlying twenty-four-decision source is dsp-extended-ai-v4 (local source: `outputs/dsp-extended-ai-v4/registration.json`).

The model remains `gpt-5.6-sol` version `2026-07-09`, `DataZoneStandard` capacity 100, with `reasoning_effort=low`. The decision output allowance is 12,288 tokens versus 8,192 in the baseline; reference surveys allow 8,192. The comparison changes prompt, response schema and output allowance, adds a reference-only response, and uses one completion per condition. It is not a randomized or isolated test of the instruction to examine every diagram.

There are fourteen unique HTTP 200 responses: six surveys and eight classifications. Two preserved source receipts carry local citation-validation failures: valid numerical citations and a valid additional ridge citation were incorrectly rejected. Corrected validation requires the appropriate reference/query diagram while allowing additional registered evidence; the responses were recovered unchanged, without repeat inference. Eleven exact responses are reused in the final continuation and three were newly obtained there. No request to change cloud infrastructure was made, and no raw model result was edited.

Usage is 900,967 prompt tokens and 66,970 completion tokens. Seven calls fit the existing short-context pricing rule and total USD 2.1472836; seven exceed its 64,000-input-token guard and remain unpriced. This is a partial estimate, not the total experiment cost. The runner depends on the [pinned DSP extension environment](../ml/requirements-dsp-extensions-windows-arm64.txt).

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_diagram_audit evaluate --output outputs/dsp-diagram-audit-v4
.\.venv\Scripts\python.exe -m pytest -q tests/test_dsp_extensions.py tests/test_audio_comparison.py
```

Evaluation rechecks the frozen runner, settings, sealed truth, registered inputs, raw response bindings, per-view schema/citations and survey dependency hashes. It makes no model calls. A new inference experiment requires a new output directory; existing request attempts cannot be overwritten.
