# EXP-012: Sol Rejects Every Real Query

The live DSP-to-Sol pipeline works technically, but the registered cross-drone classification result is negative: **0/9 known-condition trials were recognized, and all 9/9 were falsely rejected as outside-reference**. All 3/3 unknown-condition trials were also rejected. Thus every one of the twelve real decisions was outside-reference. Zero unknown false acceptance does not demonstrate useful open-set classification when no known case is accepted. No model promotion, extra reference labeling, prompt revision, silver collection, specialist training or routing followed.

The existing Azure resource was successfully reused after one user-authorized deployment retry. The exact responding model was `gpt-5.6-sol-2026-07-09`, DataZoneStandard, with NoAutoUpgrade. One synthetic gate and all twelve real calls completed without transport/parser failures or inference retries. Total estimated list-price consumption was **USD 0.72875088**, including the synthetic gate. This is an exploratory result on three repeated query clips from one query drone, not independent-acquisition population evidence.

See the [frozen protocol](DSP_LLM_PROTOCOL.md), [packet contract](DSP_LLM_FORMAT.md), [infrastructure history](DSP_RESOURCE_REUSE.md), and [exact evaluator aggregate](../ml/dsp-sol-exp012-reuse-results-v1.json).

## Actual Outcomes

| Outcome | Known trials | Unknown trials |
| --- | ---: | ---: |
| Correct known assignment | 0/9 | Not applicable |
| Wrong known assignment | 0/9 | Not applicable |
| Known falsely rejected as outside-reference | **9/9** | Not applicable |
| Unknown falsely accepted as known | Not applicable | 0/3 |
| Correct outside-reference decision | Not applicable | 3/3 |
| Indeterminate | 0/9 | 0/3 |
| Technical failure | 0/9 | 0/3 |

All twelve registered real requests were sent; none remained unsent. Known-label coverage was 0/12 and accepted-label error is undefined because no label was accepted. Non-abstaining decision coverage was 12/12, but nine decisions were wrong. The synthetic probe returned its expected C01 assignment; it validates the instrument and transport, not real acoustic diagnosis.

| Reference set | Known recognized | Known falsely rejected | Unknown correctly rejected |
| --- | ---: | ---: | ---: |
| All three conditions visible | 0/3 | 3/3 | No unknown trial |
| C01 excluded entirely | 0/2 | 2/2 | 1/1 |
| C02 excluded entirely | 0/2 | 2/2 | 1/1 |
| C03 excluded entirely | 0/2 | 2/2 | 1/1 |

| Evaluator truth | C01 predicted | C02 predicted | C03 predicted | Outside-reference | Indeterminate | Technical failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 represented | 0 | 0 | 0 | 3 | 0 | 0 |
| C02 represented | 0 | 0 | 0 | 3 | 0 | 0 |
| C03 represented | 0 | 0 | 0 | 3 | 0 | 0 |
| Entire condition excluded | 0 | 0 | 0 | 3 | 0 | 0 |

C01 is publisher normal, C02 motor-cap dent at position 1, and C03 propeller cut at position 1. Each class has one A reference and one B query; the same B queries recur across folds. Each query condition therefore contributes three falsely rejected known trials and one correctly rejected unknown trial. These are twelve reference-set trials over three distinct clips, not twelve independent acquisitions. Different drone types, background mixtures and unresolved original-take lineage remain confounds. B was already development data; protected C was not accessed.

## What The Model Used

The all-known responses emphasized query/reference differences in dominant FFT frequencies, autocorrelation periods and band-power distribution. For example, one response contrasted a query peak at 226 Hz with reference peaks at 306, 298 and 286 Hz; another contrasted a 256 Hz query with the same reference range. The model described these resolved differences as grounds to exclude all known IDs. Those explanations show the basis of its decisions, not that the exclusions are correct. Publisher truth establishes that the represented conditions should still have been recognized under this cross-drone task.

The observed spectral differences may reflect hardware or operating conditions as well as the target conditions. This experiment does not separate those causes. It establishes that the frozen comparison did not transfer the condition labels from A to B; it does not establish that DSP reports are intrinsically uninformative or that an LLM can never interpret them. No new invariance rule, speed estimate, prompt or threshold was selected after seeing the answers.

EXP-011's Welch control on the same six source clips abstained on 12/12 trials. Sol instead rejected 12/12, with no gain in correct known assignments. That earlier control is contextual evidence: its signal/feature parameters differ from this richer DSP packet, so it is not a feature-matched causal comparison of vision versus numerical analysis.

## Technical And Cost Evidence

| Measured item | Result |
| --- | --- |
| Actual model identity in every response | `gpt-5.6-sol-2026-07-09` |
| Live ARM binding before every call | Correct model/version, DataZoneStandard, Succeeded, NoAutoUpgrade |
| Synthetic calls | 1, expected C01 decision |
| Real calls | 12, all valid structured outputs |
| Inference retries | 0 |
| Image occurrences | 78 in real requests; 84 including the six-image synthetic probe |
| Input tokens, including probe | 160,905 |
| Cached input tokens | 35,072, included in input total |
| Completion tokens | 7,257, including 746 reasoning tokens |
| Unknown-usage attempts | 0 |
| Real model HTTP time | 104.606 s total; 7.045-10.780 s per request |
| HTTP time including probe | 113.655 s total |
| Real-run command wall time | 192.289 s |
| Synthetic command wall time | 16.186 s |
| Real-call estimated cost | USD 0.67450768 |
| Synthetic estimated cost | USD 0.05424320 |
| Combined estimated cost | USD 0.72875088 |

Costs use the registered public short-context Data Zone Standard rates: USD 4.40 per million uncached input tokens, 0.44 cached input and 22 completion tokens, including reasoning. They are estimated list-price consumption, not an Azure invoice. The worker's end-to-end time includes fresh ARM identity checks and CLI authentication, so it is longer than model HTTP latency. These timings are single observations, not throughput benchmarks.

All thirteen actual sent request files matched their frozen body SHA-256. Raw responses and parsed receipts agreed on outcomes, condition IDs and explanations. Every returned evidence citation referenced a visible measurement or image ID. This validates citation existence and parser integrity, not the factual correctness of every explanatory claim. The original PNG byte paths were used with `detail=high`; the API accepted image inputs. Provider-internal resizing is not exposed in the responses, and the synthetic packet also includes numerical measurements, so this is not an image-only ablation or proof of the images' independent contribution.

Three publisher annotations simulated the initial confirmed references. No additional calibration label, new human diagnosis or query correction was requested. Human minutes were not measured. Inference outputs remain experimental predictions, not gold or eligible training data.

## Retry And Provenance

The first reuse deployment failed with RequestConflict and remains recorded unchanged. On the user's explicit retry request, fresh reads found a Succeeded parent, no Sol child, and no active ARM deployment in the group. Free Data Zone Sol quota was rechecked. One new deployment, `modelmetis-sol-reuse-retry-20260929`, was submitted and completed Succeeded in 5.499 seconds, correlation `e8f22f47-77b4-493d-afde-62bcb4ddcb66`. Its child is `modelmetis-dsp-sol` on `aif-iveco-safety-test-20260918` in `rg-iveco-agent-testing-troubleshooting`, with DataZoneStandard capacity 50 and NoAutoUpgrade. No group or old model was deleted. The Global Standard quota request was not checked or resubmitted.

The preparation remained `artifacts/dsp-sol-exp012-reuse-prepared-v1/`, registration hash `fe297154c5fb966d069df7fd399ce0523ae1f0481621159f884e692d4144af37`. The live run is `artifacts/dsp-sol-exp012-reuse-run-v1/`; sealed evaluation is `artifacts/dsp-sol-exp012-reuse-evaluation-v1/`. The versioned aggregate is an exact byte-for-byte copy of the evaluator's aggregate, while request/response bodies and evaluated per-query rows remain ignored locally.

Preserved logs include deployment retry submission (21.223 s), exact frozen-input and credential checks (14.955 s), Succeeded model readback (4.343 s), synthetic probe (16.186 s), real run (192.289 s), evaluator, result accounting and live-evidence audit. The first additional audit command failed before execution because nested Python/PowerShell quoting produced a syntax error (0.154 s); the corrected structured PowerShell audit verified all thirteen calls (0.911 s). This verification-command failure did not trigger another model request.

GitHub DNS recovered during this retry. The prior credential-checked commit `15f85c9` was pushed and its remote SHA verified. Credential caches, keys, bearer tokens, raw artifacts and personal quota receipts remained outside the publication set. No attempt was deleted or rewritten to hide a technical failure or negative result.

## Decision

The reusable DSP packet, exact-version Azure endpoint, strict response parser and independent evaluator are operational. The current one-reference cross-drone method is not useful for recognizing the represented conditions in this bounded screen. Stop here: retain the negative evidence and do not expand human reference work, start silver collection or train a specialist to imitate these rejections. A different comparison hypothesis or data design requires a new explicit protocol; none was run automatically.
