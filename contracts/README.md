# Versioned Contracts

First deliverable, MM-004: JSON schemas and a v1 OpenAPI contract with positive and negative fixtures. This directory currently contains the content specification, not executable schemas.

| Contract | Required fields and invariants |
| --- | --- |
| Task | ID/version, taxonomy, allowed inputs, outputs, segments, critical classes, and review rules |
| InferenceRequest | ID, idempotency key, task/version, asset ID/hash, owner, and authorized metadata |
| Prediction | ID, request ID, status, label if available, model/version, prompt, preprocessing, score, and score type |
| RoutingDecision | Policy/version, path, reasons, eligibility, attempts, latency, and cost |
| LabelRevision | Example ID, previous revision, label, silver/verified/gold level, checks, author, and timestamp |
| DatasetManifest | Snapshot ID, examples and hashes, provenance, groups, splits, selection policy, and schema |
| EvaluationReport | Candidate, baseline, dataset, metrics, support, intervals, gate/version, and verdict |
| ModelRelease | Artifact, environment, label map, preprocessing, calibrator, policy, report, and approval |
| DomainEvent | Event ID, type/version, UTC timestamp, correlation ID, aggregate ID, and payload reference |

Use UTC timestamps, stable identifiers, and monetary values with currency, pricing date, and estimate source. A label may be absent in non-conclusive states; a missing score must not become zero. Store uncertainty, novelty, and source reliability separately.

Compatibility: optional additions within the same version; changes in meaning, taxonomy, or required fields require a new version and migration. Test consumers with duplicate, out-of-order, and unsupported-version events.
