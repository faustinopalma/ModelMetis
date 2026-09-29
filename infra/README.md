# Azure Infrastructure

This directory contains audio/DSP model templates and the roadmap for private AML/application infrastructure. AML and application cloud resources remain undeployed. [DSP resource state](../docs/DSP_RESOURCE_REUSE.md) is maintained separately.

## Current Increment

The subscription template (`infra/audio.bicep`; local-only) creates `rg-modelmetis-dev-audio-swc` in Sweden Central and invokes the account module (`infra/audio-account.bicep`; local-only). Subscription: `7ecf802f-04ac-4e81-8703-c3d39074f823`; tenant: `39d764bc-ae80-46f9-b22c-6246cc5a20c2`. Inputs are location, group name, caller principal ID, allowed IPv4 and owner. Preserve unrelated resources and CLI state.

Deployment `modelmetis-audio-20260918` created `aoai-modelmetis-dev-iydoch6uxaxx6`, model deployment `modelmetis-audio-teacher` and a scoped Cognitive Services OpenAI User role. Model: `gpt-audio-1.5@2026-02-23`, GlobalStandard capacity 100, NoAutoUpgrade. Endpoint: `https://aoai-modelmetis-dev-iydoch6uxaxx6.openai.azure.com/`. Compilation, ARM validation, four-Create what-if, security readback and real authenticated calls passed. [Diagnostic results](../docs/EXPERIMENTS.md) remain negative.

Local authentication is disabled. Networking uses default Deny, bypass None and one execution-machine IPv4 rule. GlobalStandard processing can occur outside the resource region. These templates create metered inference, with no storage, VNet, AML workspace or GPU. Future storage requires disabled public access and private endpoints/DNS.

Before a repeat deployment, verify the explicit subscription and current egress IP, compile both templates, run ARM validation and what-if, and inspect the exact change set. The resource group existed only after this deployment. Do not redeploy merely to repeat inference. The current role assignment uses principal type User and must be parameterized for a future federated CI service principal; CI readiness is not claimed. Do not store credentials or private spending ceilings in parameters, logs or documentation.

The [AML draft](../docs/AML_INFRASTRUCTURE.md) defines the proposed West Europe environment, quota/cost evidence and private data/CI boundaries. A private execution path and validated templates remain prerequisites. GPU execution and shutdown remain unverified.

## Planned Modules

| Bicep module to implement | Contents |
| --- | --- |
| Identity and access | Managed identities, least-privilege RBAC assignments, and CI federation |
| Observability | Log Analytics, Application Insights, alerts, and budgets |
| Data and messaging | Blob Storage, PostgreSQL, and Service Bus |
| Runtime | Container Registry, Container Apps environment, API, and worker |
| Teacher | Foundry resource/project and deployment of the selected model |
| ML | Azure ML workspace, dependencies, training compute, and serving |
| Networking | VNet, DNS, and private endpoints according to data classification and SKUs |

Bicep is the initial proposal for an Azure-only project; do not add Terraform alongside it without a concrete requirement. Use separate dev and prod parameters, with no secrets in parameter files. Minimum tags: project, environment, owner, and cost center.

## Before Generation

Verify tenant, explicit subscription, dedicated group, names, networking, model/SKU availability, pseudo-label usage terms and AML quotas. AML quotas can differ from Microsoft.Compute quotas. Keep private spending limits out of published parameters and logs.

## Before Deployment

Build and lint Bicep, verify APIs/SKUs, analyze RBAC, run what-if and prepare dated consumption estimates before applying authorized changes. Stop on unexpected modifications to existing resources or violations of the private-storage constraint. The runtime uses data access and inference permissions; the deployment identity has separate permissions. No `azd` project is configured here.

Azure ML online endpoints and some data services have fixed costs. Define dev operating hours and selective compute cleanup while preserving data and audit records. Azure budgets do not automatically shut down resources.
