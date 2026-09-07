# Tests

There is no executable test suite yet. Implement it alongside MM-004 and MM-005, before cloud integrations.

| Level | Scope | Dependencies |
| --- | --- | --- |
| Contract | Schemas, enums, versions, invalid inputs, and event compatibility | Local only |
| Unit | Routing, gates, revisions, idempotency, and transitions | Deterministic fakes |
| Local integration | Persistence, outbox, and concurrency | Isolated test database |
| Azure integration | Foundry, Blob, Service Bus, identity, and Azure ML | Authorized dev environment and limited budget |
| ML | Leakage-free splits, metrics, calibration, and bundles | Synthetic fixtures and small assets with valid usage rights |
| End-to-end | Teacher, collection, review, shadow, and rollback | Simulated locally; separate Azure run |
| Load and resilience | p95, throughput, 429, timeouts, backlog, and recovery | Dedicated environment, not production |

Fast tests require no secrets, GPUs, or metered calls. Live tests are explicit and do not run on external pull requests. No production images in fixtures. The final gold set is not a public fixture and is not used on every commit.

The [negative tests](../docs/VALIDAZIONE.md) are suite requirements. A test comparing zero examples must fail; mocks and simulations do not demonstrate compatibility with the real Azure API.
