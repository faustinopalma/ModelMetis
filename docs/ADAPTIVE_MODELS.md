# Adaptive Model Experiments

Frozen encoders and a fixed mixture matched the spectral baseline on Jin but failed cross-drone transfer. Learned selection, adaptive routing and online reference updates remain unimplemented. [Results and failures](EXPERIMENTS.md).

## Sparse Human Annotation Contract

Start with one labeled reference per category and occasional confirmed additions. Routine manual labeling is outside the design. A teacher may be a generative model or a frozen encoder with reference comparison and abstention.

1. Preserve individual gold recordings, labels, embeddings, preprocessing versions and annotation provenance. Centroids are derived summaries; classes with multiple acoustic modes may require multiple prototypes.
2. Acceptance must cover proximity, separation from competing classes and input quality. Distance and similarity softmax are uncalibrated; one reference cannot estimate class spread or guarantee unknown-fault rejection.
3. Abstain on novel, ambiguous or unusable input. Group pending cases for bounded representative review, without propagating a reviewed label as gold to the whole group. Exceeding the review allowance leaves cases unresolved or pauses operation.
4. Human review may confirm an existing condition, add a new condition, reject poor audio or leave the cause unknown. Record reviewer, evidence and corrections; new conditions require a taxonomy revision.
5. Version reference additions and test regressions before activation. Preserve predictions made before review. Algorithmic labels remain silver and cannot move gold prototypes.
6. Measure accepted-label error, automatic coverage, per-class recall, unknown false acceptance, unresolved cases and total human effort. Include initial annotation, calibration, corrections and audits of accepted predictions. Review allowance and acceptable risk/coverage remain unspecified.

Publisher-derived supports use `simulated_human_from_publisher`; query references stay sealed. A reviewed sample is no longer an independent future test sample. Adaptive experiments require a registered predict-before-review stream and untouched confirmation data.

Implemented: frozen embeddings, centroid comparison, uniform mixtures and a support-only geometric rejection rule. Pending: calibrated novelty/ambiguity handling, gold-reference updates, review grouping/limits, selective-risk validation and online silver collection. EXP-009's rejection rule had zero coverage; EXP-010's clusters remained impure.

## EXP-009: Cross-Drone Sparse-Reference Test

Hypothesis: nine A references support classification of the same nine conditions on B, with support-only rejection limiting errors. The importer verifies the v5 audit and archive hashes, requires complete labeled two-microphone keys, and exports microphone 1. Keys include drone, maneuver, fault, source index, background, background index and SNR. Lowest decoded-PCM hash selects one support per A class and one query per B class/maneuver; source-path tie breaking is restricted to the importer. Each drone is one physical group. C is excluded.

The nine supports and 54 queries use opaque IDs, separated labels and duplicate checks. Canonical audio is mono 16 kHz PCM16, 8,000 samples, DC-centered and peak-scaled to 0.95. Published feature padding is retained; waveforms are not repeated or concatenated. Synthetic half-second probes precede real inference.

Fixed candidates: Welch/logistic, FISHER-small, ECHO-small and EAT-base30 from the EXP-008 checkpoints. Sequential CPU workers have 600-second deadlines. The uniform mixture averages all completed encoders before evaluation, requires at least two members and includes every member's cost. No query-driven model choice, extra support, threshold fitting or checkpoint change is allowed.

For each encoder, L2-normalize embeddings/prototypes and set each acceptance radius to half its minimum Euclidean distance to another class prototype. Accept only strictly inside the nearest prototype's radius; zero radii, invalid inputs and boundary ties reject. Store forced and selective predictions separately. The logistic control and probability mixture have no geometric rejection policy.

Evaluation reports accuracy, macro-F1, per-class recall/confusion, accepted count/error, coverage, abstentions and load/support/query time. Zero accepted cases gives undefined accepted error. All categories are known, so unknown-fault acceptance is not measured. [Completed result](EXPERIMENTS.md#exp-009-cross-drone-one-shot-and-abstention): forced accuracy 4-9/54, each geometric policy abstained on 54/54. No operational silver or promotion followed.

## EXP-008: Frozen Encoders And One-Shot Classification

Hypothesis: frozen pretrained audio representations plus four support labels improve on the generative teacher. Use the existing Jin four front-direction supports and twelve right-direction queries. The spectral baseline already scores 12/12; matching it, measuring cost and exposing failures are the available outcomes on this split.

Attempt FISHER-small, ECHO-small, BEATs Iter3 and EAT-base30 in that order. Inspect custom code, pin revisions and hash weights/source. Run sequential float32 CPU workers, four Torch threads, seed 17 and a 600-second whole-process deadline. Keep query labels and source identifiers out of inference and fitting.

Use published FISHER/ECHO concatenated band CLS representations at native sample rate; use EAT mean non-CLS features after 16 kHz resampling. Retain the published 1024-frame limits. BEATs was specified with mean temporal features and 16 kHz input but its weights were inaccessible. Fit cosine centroids from the four support labels. Average successful candidates' temperature-1 softmax scores uniformly, with fixed class order and full query coverage; scores are uncalibrated.

| Method | Correct | Macro-F1 | Median query seconds | Load seconds | Four-support extraction seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| FISHER-small | 12/12 | 1.000000 | 1.400829 | 37.248771 | 6.781987 |
| ECHO-small | 12/12 | 1.000000 | 0.783360 | 4.129145 | 5.600272 |
| EAT-base30 | 12/12 | 1.000000 | 1.011333 | 10.625860 | 4.002088 |
| Uniform mixture | 12/12 | 1.000000 | 3.203773 | 52.003776 | 16.384347 |
| Historical Welch/logistic | 12/12 | 1.000000 | 0.039365 | Unmeasured | Not comparable |
| Historical GPT Audio | 6/12 | 0.375000 | 8.550382 | Not comparable | Sent per request |

BEATs official Iter3 weights returned HTTP 403. EAT first failed on a missing nested dynamic-module cache file; strict loading of the same pinned local package succeeded. The preliminary two-member mixture was not evaluated; the final three-member mixture was frozen before sealed evaluation.

Runtime was x64 Python 3.13.13 under Windows ARM64 emulation. Timings are single observations; query time combines preprocessing, extraction and classification, while mixture time sums member costs and cached averaging. No GPU or paid endpoint was used. Jin's four query recordings have unknown motor/session independence and encoding confounds. No support expansion or promotion followed.

The aggregate (`ml/encoder-jin-v1.json`; local-only) retains revisions, hashes, dimensions, attempts, metrics and package versions. [Reproduction commands](LEGACY_COMMANDS.md#frozen-encoder-experiment) and runtime pins (`ml/requirements-encoder-windows-x64.txt`; local-only) describe execution. Frozen local registrations retain the exact pre-inference protocol.

## Next Stages And Acceptance Conditions

| Stage | Status | Required evidence |
| --- | --- | --- |
| Single encoders and fixed mixture | Completed | Jin results above; technical failures retained |
| Sparse-reference transfer and abstention | Failed in EXP-009 | New hypothesis and independent acquisitions before another attempt |
| Learned model choice/mixture weights | Not started | Separate selection partition; untouched confirmation; equal-weight/single-model controls |
| Per-request routing | Not started | Validated abstention, error, coverage, human effort, latency and total cost |
| Experiment coordinator | Not started | Registered actions, independent gates, resource limits and reproducible versions |
| Learning from arrivals | Not started | Predict-before-review evidence, reference versioning and reversible updates |

The coordinator cannot modify sealed truth, relax gates after results or promote itself. The current ensemble averages predictions; it is not a trained mixture-of-experts network.

## Research Basis

[FISHER v3](https://arxiv.org/html/2507.16696v3) and [ECHO v4](https://arxiv.org/html/2508.14689v4) target industrial representations but pretrain on general audio/music corpora. FISHER lists AudioSet, Freesound, MTG-Jamendo and Music4all; ECHO lists AudioSet, MTG-Jamendo and Freesound from WavCaps. Their headline benchmarks generally use many labeled references. FISHER's separate few-shot study reports 28.50% one-shot and 38.98% five-shot mean accuracy over 1,500 recording-channel-separated episodes, with 15 queries/class; it is not whole-device holdout.

- [FISHER checkpoint](https://huggingface.co/jiangab/FISHER-small-0723): approximately 22M parameters, MIT model card.
- [ECHO checkpoint](https://huggingface.co/yucongzh/echo-small-0824): approximately 22M parameters, MIT; distinct from ECHOv2.
- [BEATs](https://github.com/microsoft/unilm/tree/master/beats): general audio encoder; anomaly detection does not supply fault identities.
- [EAT](https://github.com/cwx-worst-one/EAT), [base30 checkpoint](https://huggingface.co/worstchan/EAT-base_epoch30_pretrain): self-supervised audio encoder, MIT model card.
- [RMIS leaderboard](https://jianganbai.github.io/RMIS/leaderboard.html): sound, vibration and electrical protocols must be compared separately.

Exact checkpoint availability in Foundry was not verified. Local execution does not depend on Foundry or Fabric hosting.
