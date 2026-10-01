# Adaptive Class Memory Increases Unsafe Assignments

**Do not promote the tested adaptive-memory policy or open the reserved set to validate it.** On the same 72 Ottawa stream acquisitions, adaptive cards increase correct automatic recognitions from 16 to 18 but increase wrong automatic assignments from 11 to 41. Automatic coverage rises because many previously reviewed cases receive incorrect labels. The fixed-memory arm is also unreliable: 11 of its 27 accepted decisions are wrong. These results concern one registered report-based policy, not every possible multimodal or adaptive method.

The [protocol](DSP_MEMORY_PROTOCOL.md) fixes whole-acquisition isolation, 24 initial labeled examples, two arms, bounded retrieval and at most 16 publisher-oracle reviews per arm. Both streams completed. All 32 acquisitions from reserved profiles 5 and 7 remain unmaterialized and unevaluated. Same-motor dependence and prior project exposure remain; this is a development comparison, not independent-machine or clean final validation. External published scores remain contextual references and were not reproduced.

## More Coverage Does Not Mean Better Recognition

Every stream class was present in the seed bank. Each row below counts acquisitions after any allowed retrieval but before human correction; two model stages do not create two independent test examples.

| Outcome | Fixed cards | Adaptive cards |
| --- | ---: | ---: |
| Stream acquisitions | 72 | 72 |
| Correct automatic recognition | 16/72 | 18/72 |
| Wrong automatic assignment | 11/72 | 41/72 |
| Review required | 45/72 | 13/72 |
| Automatic coverage | 27/72, 37.5% | 59/72, 81.9% |
| Errors among accepted labels | 11/27, 40.7% | 41/59, 69.5% |
| Simulated human reviews consumed | 16 | 13 |
| Unresolved after review budget exhaustion | 29 | 0 |
| Total labels revealed, including 24 seeds | 40 | 37 |
| Final bank size | 24 | 37 |
| Model decisions, including retrieval stages | 128 | 105 |

The fixed arm reaches its 16-review limit and leaves later review-required cases unresolved. The adaptive arm never exhausts its review budget, but that lower intervention count is not a benefit by itself: many accepted labels are wrong. All 29 simulated human answers match the publisher labels exactly; no model-generated label is admitted into either bank. No actual human accuracy or annotation time was measured.

The matched transition table identifies where the larger acceptance rate comes from. In 34 of the 45 cases reviewed by the fixed arm, the adaptive arm assigns a wrong class; only two of those cases become correct automatic recognitions.

| Fixed outcome | Adaptive correct | Adaptive wrong | Adaptive review | Total |
| --- | ---: | ---: | ---: | ---: |
| Correct | 15 | 1 | 0 | 16 |
| Wrong | 1 | 6 | 4 | 11 |
| Review | 2 | 34 | 9 | 45 |

## Errors Persist Across Classes And The Stream

Each class contributes nine whole stream acquisitions. The columns retain the order correct / wrong / review, so a class with no accepted cases is not presented as perfectly classified.

| Publisher class | Fixed correct / wrong / review | Adaptive correct / wrong / review |
| --- | ---: | ---: |
| C01 healthy | 5 / 2 / 2 | 6 / 2 / 1 |
| C02 rotor unbalance | 1 / 2 / 6 | 1 / 7 / 1 |
| C03 rotor misalignment | 3 / 1 / 5 | 3 / 6 / 0 |
| C04 stator winding | 0 / 0 / 9 | 2 / 6 / 1 |
| C05 voltage unbalance | 0 / 3 / 6 | 0 / 9 / 0 |
| C06 bowed rotor | 2 / 1 / 6 | 2 / 3 / 4 |
| C07 broken rotor bars | 1 / 2 / 6 | 1 / 2 / 6 |
| C08 faulty bearing | 4 / 0 / 5 | 3 / 6 / 0 |

Across successive blocks of 24 acquisitions, fixed correct/wrong/review counts are 6/5/13, 3/4/17 and 7/2/15; adaptive counts are 7/10/7, 4/16/4 and 7/15/2. Thus the later reduction in review does not coincide with improved recognition. Among the 41 adaptive errors, 18 predict C07, nine C06 and seven C04. These concentrations identify useful offline inspection targets, not verified mechanical causes or proof of why the model reasoned incorrectly.

The observations are consistent with broader class references weakening rejection without preserving class discrimination. They do not establish that interpretation causally: each arm has one completion per supplied stage, updates depend on prior decisions, and stochastic differences can occur even with identical initial inputs. The study does not isolate summary rendering, representative selection, retrieval distance or the model's use of numeric controls. Adding examples alone is not an observed solution to the [Ottawa family-overlap problem](DSP_FAMILY_SEPARATION.md).

## Distinguish Model Latency From Runner Throughput

| Measured quantity | Value | Denominator and scope |
| --- | ---: | --- |
| HTTP model latency, median | 9.11 s | 232 newly executed calls in the completed campaign |
| HTTP model latency, mean | 9.63 s | Same 232 calls |
| HTTP model latency, empirical 95th-percentile order statistic | 13.54 s | Same 232 calls |
| HTTP model latency, minimum / maximum | 5.93 / 23.45 s | Same 232 calls |
| Request execution including authentication/validation, median | 13.39 s | Same 232 calls, excluding outer orchestration |
| Interval between successive completed calls, median | 62.29 s | 231 intervals, including local orchestration |
| First-to-last completion interval | 4.32 h | Completed campaign only; excludes initial setup/recovery |

The runner is serial and enforces a 25-second quota interval after the prior response, reduced by intervening local work. It repeatedly verifies complete request/response histories, replays state journals, loads DSP arrays, renders changed class cards and rechecks the target through Azure CLI. This overhead, not HTTP inference alone, explains the low end-to-end throughput. A single post-run measurement took 0.93 s for frozen-input verification, 4.34 s and 3.52 s for the fixed/adaptive full journals, and 7.27 s for all live receipts. Those are end-of-run replay measurements, not per-request historical timings or a complete profiler attribution. Optimize redundant local work before another campaign; retain one-time admission checks and append-only integrity rather than removing provenance checks indiscriminately.

## Preserve The Two Contract Recovery Attempts

There were 234 actual HTTP calls, all returning HTTP 200, and 233 scored model decisions. The first response used explanatory phrases inside `evidence`, which was incompatible with the exact-ID validator. A new request version constrained every evidence item to its allowed identifier. The second response was a valid acceptance with an empty retrieval-candidate list; the local validator incorrectly required the accepted class in that list. Correcting that check preserved valid class/query citation requirements. The exact second response was adopted once into the final campaign only after verifying identical request bytes, without another HTTP call or response-text repair.

All original attempts, responses, preparation folders and frozen source snapshots remain retained. The final campaign contains 232 new calls plus that one reused valid response, with zero unresolved technical failures. No diagnostic choice, reference selection or stream order was selected from these format recoveries, and the eight seed-card image hashes are unchanged. The reference protocol and renderer were not tuned after observing scored stream truth.

Total usage across all actual calls is 3,821,300 prompt tokens and 80,022 completion tokens. Every call fits the registered short-context accounting range. Estimated cost is USD 18.3917272: USD 18.257448 for new final-campaign calls plus USD 0.1342792 for the two original attempts. The reused response is not billed twice. These are estimates using the frozen price settings, not an invoice. No resource, deployment capacity or model version was changed.

## Reconcile Results Without Further Inference

Local evidence is retained in `outputs/dsp-memory-ottawa-v3`: `live/results.json` owns transport-verified aggregate outcomes; `states/` preserves original decisions and oracle updates; `requests/` holds bound requests, original responses and live receipts; `sealed/truth.json` is evaluator/oracle-only. The v1/v2 folders retain the two original attempts. These paths are local evidence, not committed public links. The existing GitHub Pages snapshot remains unchanged.

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_memory_inference evaluate --output outputs/dsp-memory-ottawa-v3
.\.venv\Scripts\python.exe -m scripts.dsp_memory_experiment status --output outputs/dsp-memory-ottawa-v3
.\.venv\Scripts\python.exe -m pytest tests/test_dsp.py tests/test_dsp_extensions.py tests/test_audio_comparison.py -q
```

Evaluation validates response and state bindings before reporting outcomes. The affected suite passes 61 tests. All 96 materialized acquisitions belong to the 24 seeds and 72 stream cases, and no reserved acquisition was analyzed. A new design should first inspect the incorrect acceptances offline; this failed safety comparison does not authorize spending the reserved set or launching additional model calls.
