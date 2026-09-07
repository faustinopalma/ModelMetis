# Application Core

Directory reserved for the future Python package, with no code or packaging metadata yet. The domain must be testable without Azure and without installing PyTorch or an agent framework.

Modules to introduce when required by the backlog:

| Module | Responsibility |
| --- | --- |
| `domain` | Tasks, predictions, revisions, snapshots, and releases |
| `routing` | Eligibility, abstention, fallback, and reasons |
| `teachers` | Provider interface and Foundry adapter |
| `students` | Specialist bundle invocation and validation |
| `data_engine` | Provenance, selection, deduplication, and snapshots |
| `review` | Assignment, concurrent revisions, and adjudication |
| `lifecycle` | States, budgets, training requests, and approvals |
| `adapters` | Blob, PostgreSQL, Service Bus, and Azure ML |
| `telemetry` | Correlation, metrics, and sensitive-data redaction |

The API and worker call the same application services. Transitions are persistent and deterministic. A future agent may use restricted tools to read reports and propose actions; it cannot independently change gates, privileges, or budgets.
