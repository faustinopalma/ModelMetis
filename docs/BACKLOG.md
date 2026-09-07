# Initial Backlog

All items are not started. Order and dependencies follow the [plan](PIANO.md). Roles represent responsibilities to assign, not people already committed.

| ID | Priority | Activity | Role | Depends on | Completion criterion |
| --- | --- | --- | --- | --- | --- |
| MM-001 | P0 | Select data and taxonomy | Domain, ML | None | Usage rights verified; classes and critical cases documented |
| MM-002 | P0 | Define gold-label protocol and splits | Domain, ML | MM-001 | Disjoint groups, reviewers, and adjudication rules |
| MM-003 | P0 | Approve gates and workload | Domain, backend | MM-002 | Metrics, margins, minimum support, and SLOs specified |
| MM-004 | P0 | Implement v1 contracts | Backend, ML | MM-001 | Schemas with valid and invalid cases; versioned taxonomy |
| MM-005 | P0 | Pin toolchain and establish local CI | Backend, ML | MM-004 | Reproducible environment, lint, and tests without Azure |
| MM-006 | P0 | Complete simulated teacher flow | Backend | MM-004, MM-005 | Request, prediction, audit, and feedback with idempotency |
| MM-007 | P0 | Confirm Azure destination and budget | Platform, security | MM-003 | Subscription, region, quotas, roles, licenses, and cost estimate |
| MM-008 | P0 | Implement and validate dev IaC | Platform | MM-006, MM-007 | Valid Bicep, reviewed what-if, and deployment approval |
| MM-009 | P0 | Connect teacher and measure baseline | Backend, ML | MM-008 | Benchmark with fixed model and prompt; tracked costs |
| MM-010 | P1 | Implement persistence, outbox, and worker | Backend | MM-009 | Retries and duplicate deliveries tested without logical duplicates |
| MM-011 | P1 | Build review console | Frontend, domain | MM-010 | Concurrent revisions handled and corrections auditable |
| MM-012 | P1 | Implement snapshots and lineage | ML, backend | MM-010, MM-011 | Reproducible manifest and blocking leakage check |
| MM-013 | P1 | Train baseline and specialist | ML | MM-003, MM-012 | Reproducible Azure ML job and complete release |
| MM-014 | P1 | Implement calibration and offline gates | ML, domain | MM-013 | Pass/fail/inconclusive report with intervals and segments |
| MM-015 | P1 | Implement application shadow and hybrid policy | Backend, ML | MM-014 | Paired predictions; shadow execution does not affect the result |
| MM-016 | P1 | Implement canary, approval, and rollback | Backend, platform | MM-015 | Protected transitions and tested recovery |
| MM-017 | P1 | Build dashboard for drift and total costs | Backend, ML | MM-009, MM-010 | Baseline visible immediately; hybrid comparison completed after MM-015 |
| MM-018 | P1 | Run complete demo and final report | Team | MM-016, MM-017 | Gates verified or non-promotion justified |
| MM-019 | P2 | Benchmark teacher portfolio | ML | MM-018 | Least expensive model/configuration within the same gates |
| MM-020 | P2 | Evaluate CPU serving and possible edge export | ML, platform | MM-018 | Exported model parity and measured economic benefit |

## First Increment

Complete MM-001 through MM-006. The expected result is a testable local flow and a measurement protocol, not a collection of empty Azure services. MM-007 can proceed in parallel once a workload profile and budget are available.

## Shared Definition of Done

Each item delivers versioned artifacts, tests for the introduced behavior, and at least one negative test for critical guarantees. Do not mark a feature complete using mocks as evidence of real integration. Changes to tasks, policies, data, and models must be traceable to a release and a report.
