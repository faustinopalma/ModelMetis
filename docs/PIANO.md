# Development Plan

Date: September 7, 2026. Sources: [original idea](../idea.txt) and [original diagram](../ModelMetis.png). Status: a proposal for starting implementation, not a validated deployment plan.

## 1. Objective and Hypothesis

We want to test whether examples produced during inference, supplemented by expert review, can train a specialist that reduces cost and latency without exceeding the allowed loss in quality. The comparison covers the complete system, including the router, fallback, abstentions, and review, not just classifier accuracy.

The result may be negative: insufficient data, correlated teacher errors, excessive fallback, or high fixed costs may make the foundation-only path preferable. In that case, the candidate is not promoted and the reason is recorded.

## 2. PoC Scope

- One visual classification task for industrial components, a versioned taxonomy, and a single organization.
- Initial classes proposed in the source: no defect, surface damage, incorrect assembly, and deformation. If the data does not support a reproducible distinction, narrow the taxonomy before benchmarking.
- `unknown` denotes a condition outside the taxonomy; `abstained` means the system cannot decide. Neither means a defect-free component. Learning an `unknown` class requires representative examples and does not guarantee recognition of every novel condition.
- A multimodal teacher, data collection, human review, a versioned dataset, one specialist, shadow evaluation, canary rollout, and rollback.
- A console with a review queue and trends in quality, latency, cost, sample counts, and routing distribution.
- No automatic commands to the production line and no high-impact decisions without oversight.

We defer multi-tenancy, generalized document and sensor support, edge deployment, Kubernetes, federated learning, extensive automated architecture search, and autonomous optimization without approval. ONNX export is a possible later step, subject to parity verification of the exported model.

## 3. Decisions Required Before Cloud Deployment

| Decision | Contributors | Required outcome |
| --- | --- | --- |
| Image source and usage rights | Data owner and domain representative | Dataset usable for inference, annotation, and training |
| Taxonomy, critical classes, and error costs | Domain expert | Task definition and annotation instructions |
| Ground-truth source and reviewers | Quality and operations | Gold-label protocol, adjudication, and review capacity |
| Volume, peaks, latency, and availability | Application owner | Measurable workload profile, including image sizes |
| Minimum quality and non-inferiority margin | Domain and ML | Gates approved before examining the final test |
| Budget and operating hours | Project owner | Monthly limit and per-experiment limit |
| Tenant, subscription, region, and residency | Platform and security | Approved Azure destination and network constraints |
| Models eligible as teachers | ML, security, and legal | Availability, licenses, and terms permitting the intended use of outputs for training |

Not every decision needs to be resolved to organize the repository. These answers are required before activating paid resources or using real data.

## 4. Implementation Sequence

Durations are effort estimates for two engineers covering backend/platform and ML, with regular access to a domain expert. They are not measured times. Data access, annotation, approvals, and GPU quotas may dominate the schedule. Indicative PoC duration: 8-12 weeks with partially overlapping activities; revise the estimate after F1.

### F0. Task and Experimental Protocol

Estimated duration: 3-5 days. Dependency: none.

- Select the initial dataset and verify its license, privacy requirements, representativeness, and coverage of critical classes.
- Write annotation instructions, review rules, and disagreement-handling procedures.
- Split development data and the gold test set by component, batch, plant, and time. Deduplicate before splitting.
- Agree on metrics, margins, sample sizes, and budget according to the [validation protocol](VALIDAZIONE.md).

Done when: a manifest identifies the splits, an expert approves the taxonomy, and the protocol specifies when a result must be considered inconclusive.

### F1. Contracts and First Local Flow

Estimated duration: 1 week. Dependency: F0.

- Pin the toolchain and dependencies; implement contracts and validators with positive and negative tests.
- Implement the API, a simulated teacher adapter, a local development repository, and the `teacher_only` policy.
- Record input, decision, policy version, outcome, and provenance without storing content in application logs.
- Handle idempotency, timeouts, provider errors, invalid input, and abstention. Do not present simulated responses as real predictions.

Done when: a local test covers input, simulated inference, recording, and feedback; a teacher error does not produce a fabricated classification. Tests require no Azure credentials.

### F2. Azure Foundation and Teacher Baseline

Estimated duration: 1-2 weeks. Dependencies: F1 and approval of the destination, budget, and infrastructure.

- Verify live authentication, roles, regional availability, Foundry quotas, and Azure ML-specific quotas. Do not infer ML quotas from general VM quotas.
- Generate and validate Bicep for the dev environment; run what-if and approve the cost before provisioning.
- Connect Container Apps, Foundry, Blob, PostgreSQL, Service Bus, and observability using managed identity where supported.
- Benchmark the teacher on development data with fixed instructions and preprocessing. Compare a small set of available models, choosing the least expensive one that passes the gates, without assuming it is the largest.
- Measure cost, p50/p95 latency, errors, throughput, and quality, distinguishing gold annotations from generated labels.

Done when: an authorized input produces a traceable real result; anonymous access is denied; replaying the same request does not duplicate data; the baseline and costs have a version, date, and provenance.

### F3. Data Engine and Review

Estimated duration: 1-2 weeks. Dependency: F2.

- Implement at-least-once event delivery, idempotent consumers, an outbox, and a dead-letter queue.
- Separate silver, verified, and gold labels; syntactic validation alone does not make a label semantically verified.
- Build a review queue that includes random sampling alongside uncertain cases, so observation is not limited to errors flagged by the router.
- Preserve corrections as append-only revisions; do not overwrite previous predictions or annotations.
- Publish snapshots with hashes, provenance, splits, and selection policies. Gold test data remains excluded from few-shot examples, training, and calibration.

Done when: an example can be traced to its image, teacher, prompt, corrections, and snapshot; duplicate delivery does not create two examples; a test image cannot enter the training snapshot.

### F4. First Specialist and Offline Evaluation

Estimated duration: 1-2 weeks. Dependencies: F3 and sufficient data coverage as defined in F0, not merely a total example count.

- Start with transfer learning on an existing vision backbone and compare it with a simple baseline, such as frozen embeddings and a linear classifier.
- Train in Azure ML with a reproducible environment, versioned assets, and MLflow tracking. Do not implement networks or metrics from scratch when libraries already provide them.
- Compare gold-only training with training on filtered pseudo-labels, preserving provenance separately and measuring the effect.
- Calibrate scores and thresholds on dedicated data; evaluate noise, blur, lighting variations, and relevant segments.
- Register the artifact, preprocessing, label map, calibrator, metrics, and usage constraints as a single release.

Done when: a job reproduces the dataset and configuration, producing a candidate and a report with a `pass`, `fail`, or `inconclusive` verdict. Insufficient sample size prevents promotion.

### F5. Shadow Evaluation and Adaptive Router

Estimated duration: 1 week. Dependency: F4.

- Run the specialist in shadow through an asynchronous application branch. The returned result remains the teacher's, and shadow execution must not slow the user-facing path.
- Record paired predictions on the same input version; evaluate them against gold labels or real outcomes, not just mutual agreement.
- Implement eligibility checks for task, segment, input quality, calibrated score, novelty, and critical class.
- Calculate coverage, selective risk, the cost of running both paths, and review costs.

Done when: a controlled test shows that shadow execution does not change the response and that the router records a reproducible reason for every path.

### F6. Canary, Promotion, and Rollback

Estimated duration: 1 week. Dependencies: F5 and approval from the model owner.

- Enable the specialist for increasing percentages of eligible inputs only, with stable assignment per request or group. Proposed initial sequence: 5%, 25%, 50%, and 100% of eligible inputs.
- Each step requires a sufficient sample, temporal coverage of the processes, and passing gates. Do not promote solely because an interval has elapsed.
- Version the artifact, thresholds, segments, and policy together; retain the last approved release.
- Test administrative and automatic rollback. An unavailable foundation model or exhausted budget requires review or abstention, not forced acceptance of the specialist's prediction.

Done when: canary rollout, promotion, and rollback are auditable; an induced degradation activates the safe policy within the agreed time; the teacher retains the capacity required for fallback.

### F7. Monitoring and Final Demonstration

Estimated duration: 1 week. Dependency: F6.

- Complete the dashboard with quality metrics as ground truth becomes available, drift, fallback, review, latency, and total cost.
- Introduce a batch with new conditions, observe abstention and review, and produce a new snapshot without contaminating the locked test set.
- Allow the coordinator to propose retraining within a budget and cooldown; retain human approval for promotion.
- Run the complete demonstration and compare the foundation-only and hybrid systems on the same distribution.

Done when: the final report demonstrates that the gates are met or documents why the teacher must remain the primary path. Every metric includes a denominator, unit, period, and release version.

## 5. Roles and Dependencies

Backend/platform implements the API, persistence, events, identity, infrastructure, and CI/CD. ML implements data preparation, training, calibration, and analysis. The domain expert annotates and validates critical cases. The model owner approves promotions and rollbacks; security and the data owner approve access and retention. One person may cover multiple roles in the PoC, but inference and promotion permissions remain separate.

The main dependency is the availability of independent ground truth. Access and budget can be clarified alongside F0; adding infrastructure cannot repair a contaminated test set.

## 6. Risks to Keep Explicit

| Risk | Mitigation | Required evidence |
| --- | --- | --- |
| Incorrect but highly confident teacher | Independent gold labels and random review | Errors by class and segment |
| Agreement between models with correlated errors | Agreement as a signal, not ground truth | Comparison with annotators or outcomes |
| Leakage between frames of the same component | Group-based splits and deduplication | Manifest disjointness tests |
| Rare defects | Targeted sampling and confidence intervals | Per-class support and an inconclusive verdict when necessary |
| Lower nominal cost but not lower total cost | Include idle capacity, shadow, training, and review | Cost per valid decision and break-even |
| Drift without timely labels | Proxies, gold sampling, and conservative policy | Measured feedback delay and false alarms |
| Teacher quota exhaustion or outage | Limits, circuit breaker, and abstention | Tests for 429, timeouts, and unavailability |
| Deletion of data already used | Lineage and assessment of derived models | Retirement or retraining procedure |

## 7. Future Development

After the PoC: optimize the foundation-model portfolio with controlled benchmarks, introduce more selective active learning, and evaluate CPU serving on Container Apps followed by edge deployment. Generalize contracts and tasks only after a second real use case. Introduce Microsoft Agent Framework for analysis tools and evidence-based proposals if it provides a measurable benefit; no agent may rewrite gates, roles, or spending limits.
