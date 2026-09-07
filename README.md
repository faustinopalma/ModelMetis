# ModelMetis

ModelMetis starts with a foundation model, collects examples with verifiable provenance, and introduces specialized models when measurements justify their use. The foundation model remains available for teaching, validation, and fallback; neither path replaces human review in critical cases.

## Status

Project preparation as of September 7, 2026. The plan, proposed architecture, and implementation directories are in place. There is no application, installed dependencies, trained models, deployable infrastructure, or provisioned Azure resources yet. The subscription, region, quotas, available models, and prices have not been checked against a tenant.

The original sources are [idea.txt](idea.txt) and [ModelMetis.png](ModelMetis.png), preserved without changes.

## Getting Started

1. Read the [development plan](docs/PIANO.md), which defines the PoC scope and phase sequence.
2. Use the [Azure architecture](docs/ARCHITETTURA.md) to assign components and prepare infrastructure decisions.
3. Agree on the [validation protocol](docs/VALIDAZIONE.md) before selecting models or thresholds.
4. Start with the P0 items in the [backlog](docs/BACKLOG.md). Do not start with training or full provisioning.

## Directories

| Path | Responsibility |
| --- | --- |
| [docs](docs/PIANO.md) | Plan, architecture, validation, and backlog |
| [apps/api](apps/api/README.md) | Inference, feedback, and administration API |
| [apps/console](apps/console/README.md) | Human review and operational dashboard |
| [src/modelmetis](src/modelmetis/README.md) | Domain, routing, datasets, and lifecycle coordination |
| [contracts](contracts/README.md) | Versioned API contracts, events, and manifests |
| [configs](configs/README.md) | Tasks, prompts, and declarative policies, without secrets |
| [ml](ml/README.md) | Data preparation, training, calibration, and evaluation |
| [infra](infra/README.md) | Specification of Bicep modules to implement after approval |
| [tests](tests/README.md) | Test strategy and non-sensitive fixtures |
| [data](data/README.md) | Local data rules and Azure asset references |
| [scripts](scripts/README.md) | Reproducible automation to implement |
| [.github](.github/README.md) | Specification of future CI/CD pipelines |

## Initial Decisions

The PoC covers industrial image classification, one task, and one organization. Python for the runtime and ML, FastAPI for the API, and React and TypeScript for the console. Azure Container Apps hosts the API and worker; Microsoft Foundry exposes the teacher; Azure Machine Learning manages training, experiments, and models. Blob Storage holds images and artifacts, PostgreSQL holds metadata and state, and Service Bus carries events. The architecture document explains the rationale and alternatives.

These are proposed design decisions, not dependencies already installed. Package versions will be pinned and verified during the first implementation. No multi-agent framework is introduced into the inference path: safety and promotion decisions must be deterministic and auditable.
