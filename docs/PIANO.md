# Development Plan

The remaining goal is reliable audio classification with sparse human input and lower total inference cost. Current experiments have not met the diagnostic gate. See [current state](CONTEXT.md) and [results](EXPERIMENTS.md); this plan describes the remaining lifecycle, not deployed capability. The [original concept](../idea.txt) and [diagram](../ModelMetis.png) are retained as source material.

## Scope

One organization, one defined audio task, a versioned taxonomy, a teacher/reference algorithm, review, immutable datasets and a specialist. Evaluate the complete path, including rejection, fallback, human effort and fixed costs. `outside_reference` is a comparison outcome; it does not establish a fault. `indeterminate` records unresolved input.

Multi-tenancy, edge deployment, Kubernetes, federated learning and production-line control are outside the current scope. Video feasibility is deferred. A model is promoted only after independently measured quality and cost gates pass.

## Prerequisites

| Area | Required definition |
| --- | --- |
| Data | Usage rights, representative acquisitions, physical-unit grouping and protected confirmation set |
| Task | Supported machine family/regimes, taxonomy, critical classes and error costs |
| Review | Gold-label protocol, adjudication, reference update policy and bounded workload |
| Quality | Error limits, minimum useful coverage, per-class support and non-inferiority margins |
| Workload | Input sizes, arrival rate, peaks, latency and availability targets |
| Infrastructure | Subscription, region/residency, identities, private data path, quotas and full cost estimate |
| Models | Fixed versions, supported modalities and terms permitting output-based training |

## Implementation Sequence

| Stage | Work | Completion evidence |
| --- | --- | --- |
| F0. Protocol | Audit source/rights; define groups, taxonomy, sparse supports and gates | Frozen manifest and [validation protocol](VALIDAZIONE.md), including inconclusive outcomes |
| F1. Local contracts | Validate inputs, idempotency, provenance, feedback and failure handling | Positive/negative tests without credentials; explicit distinction between simulated and real predictions |
| F2. Teacher baseline | Validate IaC and access; connect a fixed teacher; measure independent development outcomes | Real traceable calls, bounded costs and acceptable class-level quality/coverage |
| F3. Collection/review | Outbox, idempotent workers, immutable predictions, sparse review and versioned snapshots | Duplicate deliveries are harmless; reference/evaluation data cannot enter training |
| F4. Specialist | Fit a simple baseline and candidates from eligible training snapshots; calibrate separately | Reproducible artifact, preprocessing, taxonomy, calibrator and pass/fail/inconclusive report |
| F5. Shadow/router | Collect paired teacher/specialist predictions; validate eligibility and abstention | Shadow cannot change responses; error, coverage, fallback and full cost are measured |
| F6. Canary/rollback | Version policy with model; increase eligible traffic only after gates | Protected promotion, adequate samples, preserved teacher capacity and tested rollback |
| F7. Monitoring | Track quality as truth arrives, drift, review, latency and total cost | Versioned metrics with denominators; controlled drift/recovery test without test-set contamination |

Teacher screening gates collection; sufficient class coverage gates fitting; independent evaluation gates shadow/canary. A failed stage retains the previous serving policy. The current negative results block automatic silver expansion and operational specialist promotion.

## Responsibilities

Backend/platform owns APIs, persistence, events, identity and deployment. ML owns preparation, fitting, calibration and analysis. Domain reviewers establish diagnostic truth. Model owners approve promotion/rollback; data owners and security define access and retention. Runtime identities cannot grant themselves deployment or promotion authority.

## Risks

| Risk | Required control |
| --- | --- |
| Confident teacher errors or correlated model agreement | Independent truth and audits of accepted cases |
| Leakage between related windows/channels | Physical-unit/acquisition splits, deduplication and negative tests |
| Rare faults or inadequate sample size | Per-class support, uncertainty and an inconclusive verdict |
| Nominal savings erased by other costs | Include training, idle capacity, shadow, retries, fallback and review |
| Drift with delayed truth | Measured feedback delay, conservative policy and bounded review |
| Teacher outage or exhausted quota | Circuit breaker, fallback capacity and abstention |
| Removal of source data | Lineage-based retirement/retraining assessment |

Priorities and dependencies are in the [backlog](BACKLOG.md). Model portfolios, learned routing and online updates need separate registered comparisons after reliable sparse-reference behavior is demonstrated.
