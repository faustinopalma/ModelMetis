# Operational Console

Directory reserved for the future React and TypeScript application. There is no executable UI yet.

PoC views: review queue with risk and status filters; image details with provenance and corrections; dataset list and lineage; experiments with metrics and segments; releases with approval and rollback; dashboard with quality, cost, latency, routing, and feedback delay.

Review uses version control to prevent two annotators from overwriting each other's changes. Disagreement requires adjudication. The UI distinguishes silver, verified, and gold labels and does not present uncalibrated confidence as a probability of correctness. Promotion commands are authorized by the backend, not merely hidden in the UI.

The first view to implement is review, after the API flow is testable. The dashboard reads real metrics with periods and denominators; any demonstration data must be clearly separated from production.
