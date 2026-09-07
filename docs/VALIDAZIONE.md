# Validation Protocol

Status: the protocol must be completed with domain input and baseline requirements during phase F0 of the [plan](PIANO.md). No experimental results or approved thresholds are claimed. A gate without an approved value or sufficient evidence blocks promotion.

## Data and Independence

Separate training, development, calibration, and the final gold test set by physical component, batch, and time. Images of the same component, transformations, and near-duplicates belong to the same group. Test data must not appear in few-shot examples, labels used for training, or threshold selection. For rare defects, plan targeted sampling and state the prevalence; do not report an average from artificially balanced classes as a production estimate.

Use independent gold labels for promotion, with qualified annotators, disagreement review, and versioned instructions. Measure human disagreement as well. Subsequent industrial outcomes may update ground truth while preserving revisions and provenance.

Use the final test after freezing the candidate. If the candidate is modified in response to its results, a new holdout or a protocol explicitly handling repeated evaluation is required. Development checks must not continually reuse the same test set.

## Required Comparisons

1. Foundation-only with a fixed task, prompt, and configuration.
2. The specialist in isolation, including calibration and behavior on unknown cases.
3. The complete hybrid system, including teacher requests following a student attempt, abstentions, and review.
4. Ablation comparing gold-only training with training using selected silver/verified labels, when sample size permits.

Use the same inputs and segments, record pairings by request, and report confidence intervals for differences. Use group-level bootstrap for aggregate metrics and binomial intervals for per-class recall when the assumptions are appropriate. For dependent data, do not treat consecutive frames as independent observations.

## Gates to Specify

| Dimension | Measure | Acceptance rule |
| --- | --- | --- |
| Overall quality | Macro-F1 and confusion matrix | Lower confidence bound of the difference from the teacher exceeds the allowed negative margin |
| Critical defects | Recall and false-negative rate by class | Absolute minimum and margin against the baseline approved by domain experts |
| Segments | Metrics by line, batch, lighting, and image quality | No required segment below its minimum; insufficient support blocks that segment |
| Calibration | Brier score, reliability curve, and ECE with specified bins | Thresholds selected on the calibration set, then frozen |
| Routing | Coverage, selective risk, and fallback | Quality on accepted and escalated cases, without hiding abstentions from the denominator |
| Novelty | Incorrect acceptance on out-of-taxonomy sets | Agreed limit on documented scenarios, without a promise to detect all OOD inputs |
| Latency | End-to-end p50/p95 | SLO at the stated load, including cold starts and fallback |
| Capacity | Requests/s, errors, and backlog | Nominal and peak loads sustained within approved limits |
| Cost | Total cost per valid decision | Agreed minimum savings and break-even at the expected volume |
| Recovery | Time from signal to activation of the safe policy | Agreed rollback target verified through fault injection |

Numerical values, confidence level, and sample sizes must be fixed before the final comparison. As a planning example, with zero errors on approximately 300 independent examples of a class, the approximate rule of three gives a one-sided 95% upper bound on the error rate near 1%. This is not a guarantee if examples are correlated and does not justify choosing 300 as a universal sample size.

A favorable average is not enough. Critical classes and segments must have sufficient support; multiple comparisons and repeated checks require an appropriate statistical protocol. An `inconclusive` verdict is not a `pass`.

## System Cost

Define `C_total` as the sum of student inference, teacher inference, shadow execution, verification, amortized training, idle serving, runtime, storage, networking, telemetry, and human review. Cost per valid decision is `C_total / N_valid`, with an explicit definition of a valid decision and the time window. Separate cloud and human costs without excluding the latter from the economic comparison.

For a preliminary estimate: if `F` is the incremental fixed cost over the same period and `c_base - c_hybrid` is the variable saving per request, break-even is `N = F / (c_base - c_hybrid)` only if the denominator is positive and quality passes the gates. Measure `c_hybrid` on actual paths: a student attempt followed by the teacher incurs both costs. One-time and recurring training costs must have a stated amortization horizon.

## Mandatory Negative Tests

- Corrupted input, unsupported type, oversized image, or reference to another user's asset: verifiable rejection.
- Teacher 429, timeout, invalid schema, or uncertain response: bounded retries and abstention/review, never a default label.
- Student with a high score on a novel image: the test measures OOD detector error without assuming the confidence score resolves it.
- Duplicate event delivery and a crash between commit and publication: no logical duplicates; attempt costs are retained.
- The same group appears in training and test: snapshot validation fails.
- Teacher/student agreement alone, without gold labels: promotion is denied.
- A critical segment lacks enough labels: promotion is denied for that segment.
- Artifact, calibrator, or label map incompatible with the policy: release loading is denied.
- Promotion attempted with an inference role or an expired report: the operation is denied and audited.
- Degradation and rollback while the teacher is unavailable: safe abstention/review state, without loops.
- Logs containing sensitive data: redaction tests cover both text and serialized JSON, including escaped Unicode sequences.
- Critical guarantees tested with a negative control: temporarily alter behavior in a fixture or mock and verify that the test fails.

## Final Demonstration

Prepare a reproducible sequence of authorized inputs: teacher cold start, collection, review, snapshot, training, offline report, shadow, canary, a novel case triggering fallback, and rollback. Show versions, reasons, review status, and metric changes in the console.

Demonstrating fallback on a selected image does not establish general robustness. The report separates functional tests, statistical benchmarks, and load tests, and states what has not been verified. The final criterion is passing the gates for the complete system, not merely completing the demo successfully.
