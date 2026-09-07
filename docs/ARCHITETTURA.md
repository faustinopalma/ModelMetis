# Azure Architecture

Date: September 7, 2026. Proposal for the PoC described in the [plan](PIANO.md). The listed resources have not been created; SKUs, region, networking, and identities must be confirmed before generating deployable infrastructure.

## Mapping the Diagram to Components

| PNG block | Application component | Proposed Azure service |
| --- | --- | --- |
| 1. Input | Image acquisition and validation API | Container Apps and private Blob Storage |
| 2. Foundation model | Multimodal teacher adapter | Model deployment in Microsoft Foundry |
| 3. Data engine | Worker, review, snapshots, and lineage | Container Apps, Service Bus, PostgreSQL, Blob Storage |
| 4. Train & evaluate | ML pipelines and release registry | Azure Machine Learning, on-demand compute, and MLflow |
| 5. Adaptive router | Deterministic runtime policy | Container Apps and an Azure ML managed online endpoint for the specialist |
| 6. Monitor & adapt | Telemetry, delayed evaluation, and retraining | Azure Monitor, Application Insights, Log Analytics, and Azure ML jobs |
| Central runtime | Persistent lifecycle coordinator | Application worker and transactional state in PostgreSQL |

## Stack and Boundaries

Python is proposed to share contracts and logic across the API, worker, and ML, avoiding duplicate implementations of preprocessing and metrics. FastAPI handles HTTP transport; the domain does not depend on FastAPI or Azure clients. React and TypeScript are proposed for the review console. Azure dependencies and heavy training dependencies will be separated from the core and pinned in lockfiles after verifying the installed APIs.

A monorepo contains a modular core and a few deployable processes: API, worker, and console. A separate microservice is not needed for every block in the diagram. The router controls inference; the coordinator manages snapshots, experiments, and promotion requests. The language model may explain results or propose experiments, but it does not authorize privileged operations.

## Inference Flow

1. An authenticated client submits a reference to an image acquired through the API. The server checks asset ownership, actual file type, size, decoding, task, and idempotency key. It does not accept arbitrary URLs for server-side download.
2. The API records the input and acquires an immutable policy version. Initially, every valid input goes to the teacher; unusable images or cases requiring mandatory review may trigger immediate abstention.
3. In hybrid mode, the router checks preliminary eligibility, invokes the specialist, and applies subsequent checks on calibrated score, novelty, and predicted class. A suspected critical defect requires the review specified by the task.
4. If the specialist is ineligible or abstains, the runtime tries the teacher within the timeout and budget. The teacher must comply with the schema; its self-reported score is not treated as a calibrated probability. If it cannot resolve the case, the outcome is `pending_review` or `abstained`.
5. The result, routing decision, and outbox record are written in the same transaction. The response distinguishes `completed`, `pending_review`, `abstained`, and `failed` and never returns an old label as a successful result for the current request.
6. The worker publishes the event and handles collection, review, and shadow execution outside the synchronous path. Outbox records may be published more than once: consumers and writes must be idempotent.

Blob Storage and the database do not share a transaction. Uploads have a temporary state, hash, and expiry; a job reconciles orphaned assets. The request ledger uses leases and persistent state to prevent concurrent processing. A crash between the provider response and commit may require repeating a call: record attempts and cost without promising exactly-once execution against external providers.

## Persistence and Data

- Blob Storage holds inputs, manifests, reports, and artifacts. Messages contain identifiers and authorized references, not images or credentials.
- PostgreSQL holds tasks, requests, predictions, label revisions, the review queue, outbox, experiments, and releases. Transactions and unique constraints simplify lineage, concurrency, and approvals.
- Service Bus decouples processes with bounded retries and a dead-letter queue. The application does not rely solely on broker deduplication.
- An Azure ML data asset points to a snapshot with hash-addressed content and a manifest. Versioning a reference does not make the underlying file immutable: do not overwrite referenced blobs.
- MLflow records parameters, metrics, and artifacts; the Azure ML registry identifies the model. The application release binds the model, environment, preprocessing, label map, calibrator, and policy.

`verified` labels record which verification was performed; teacher-student agreement does not make them gold. Corrections and disagreements are preserved. No automation promotes a system prediction to independent ground truth.

## Training and Serving

Azure ML runs separate components for preparation, training, calibration, evaluation, and registration. Use GPUs only when the experiment requires them; configure training compute with a minimum of zero nodes where supported, concurrency limits, and timeouts. Retained caches and artifacts still incur costs.

For the first PoC, an Azure ML managed online endpoint is proposed for the specialist to keep versions and the release lifecycle explicit. The VM assigned to the deployment incurs costs even without requests: do not assume scale-to-zero for this serving option. After benchmarking, compare it with a CPU container in Container Apps; adopt that alternative only after measuring latency, cost, and prediction parity.

The Foundry teacher and Azure ML student are not two deployments of the same endpoint. Shadow evaluation between them must be implemented by the application, with request correlation and prediction recording. Native Azure ML mirroring is useful between deployments of the same endpoint, but it does not replace this comparison and does not return the shadow result to the client.

## States and Permissions

The proposed progression is `teacher_only -> collecting -> training -> offline_evaluation -> shadow -> canary -> specialized_default`. These are specialization lifecycle states: during collection, training, and evaluation, serving continues under the last approved policy. A failed candidate returns to collection without replacing the champion. A rollback reactivates a known release or `teacher_only`; if the teacher is unavailable, the policy requires abstention or review.

Each transition records preconditions, author, evidence, timestamp, and previous version. The coordinator may request training within a budget; promotion requires approval and a valid report. Release writes use concurrency control to prevent simultaneous promotions. Rollback does not delete audit records, models, or data.

## Security

- Microsoft Entra ID for users and APIs, with separate application roles for invocation, review, and approval. An authenticated token does not automatically authorize access to every asset or task.
- Separate managed identities for the API, worker, training, and deployment, with least-privilege permissions on individual services. The runtime identity cannot create resources or approve models.
- GitHub Actions with OIDC federation for future pipelines; no persistent credentials in the repository. Key Vault is reserved for unavoidable secrets from external integrations.
- Private Container Registry for application images; no admin passwords in the runtime. Pin images by digest and scan dependencies before promotion.
- Private data, TLS, access control, and dev/prod separation. For sensitive data, design the VNet, private endpoints, DNS, and runner connectivity before provisioning. Some options require more expensive SKUs: do not promise private networking on every tier.
- Do not store images, full prompts, sensitive outputs, or tokens in logs. Record identifiers, structured reasons, versions, and measurements. Image content and OCR text are untrusted inputs, never administrative instructions.
- Define retention by category, deletion of originals and copies, lineage of derived models, and retirement/retraining assessment. Backup and soft-delete retention must be compatible with deletion obligations.

## Observability and Continuity

OpenTelemetry links requests, model calls, messages, and jobs through correlation IDs. Application Insights and Log Analytics collect technical telemetry; the transactional ledger remains the source for audit records and per-request costs, rather than sampled traces.

Metrics: p50/p95, throughput, 429 responses, timeouts, schema errors, queue backlogs, pending reviews, specialist coverage, fallback and abstention, cost per valid decision, gold-label quality by segment, outcome delay, and drift. Drift is a signal to investigate, not automatic proof of degradation.

Timeouts, retries with backoff, and circuit breakers are bounded by the request budget. Teacher capacity must also support a full rollback. Explicitly test quota and budget exhaustion: no endless fallback and no silent relaxation of gates.

## Costs and Alternatives

A reliable monetary estimate requires the region, models, traffic, image sizes, serving hours, and review workload. Each estimate item must include its date, currency, rate, quantity, and source.

| Item | Drivers to measure or estimate |
| --- | --- |
| Foundry | Requests, image/text tokens, outputs, retries, validations, and fallback |
| Specialist serving | SKU, replicas, operating hours, peaks, and idle capacity |
| Training | CPU/GPU SKU, hours per job, number of experiments and evaluations |
| Runtime and data | Container Apps, PostgreSQL, Service Bus, ACR, storage, transactions, and networking |
| Observability and security | Log ingestion, retention, Key Vault, private endpoints, and DNS |
| Review | Minutes per example, sampling, adjudication, and reviewer cost |

Set budgets and alerts, but treat them as notifications, not an automatic cap on Azure spending. Application limits on concurrency, teacher requests, experiments, and compute hours provide operational controls. Shutting down dev resources must not delete datasets or audit records.

AKS is not required for the PoC. AI Search is unnecessary without a retrieval requirement. Cosmos DB remains an alternative if access patterns and scale justify it; initially, PostgreSQL provides transactions and relationships useful for the review lifecycle. API Management can be introduced for multi-client exposure or shared governance requirements; it is not a prerequisite for the first complete cycle.

## References

Microsoft sources consulted for routing and workers; actual availability in the subscription remains to be verified.

- [Azure ML: online endpoints and assigned compute costs](https://learn.microsoft.com/azure/machine-learning/concept-endpoints-online?view=azureml-api-2)
- [Azure ML: progressive rollout and mirroring limits](https://learn.microsoft.com/azure/machine-learning/how-to-safely-rollout-online-endpoints?view=azureml-api-2)
- [Container Apps: scaling and scaler authentication](https://learn.microsoft.com/azure/container-apps/scale-app)
- [Container Apps: event-driven jobs](https://learn.microsoft.com/azure/container-apps/tutorial-event-driven-jobs)
