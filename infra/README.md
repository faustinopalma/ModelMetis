# Azure Infrastructure

This directory contains the infrastructure work specification, not deployable Bicep templates. The presence of the plan does not implicitly authorize provisioning.

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

Confirm the tenant, subscription, resource group, allowed regions, naming, budget, networking, teacher model, and SKUs. Verify model availability, pseudo-label usage terms, and actual Foundry and Azure ML quotas. Azure ML compute quotas do not necessarily match Microsoft.Compute quotas.

## Before Deployment

Build and lint Bicep, verify APIs/SKUs, analyze RBAC, run what-if, prepare an estimate with dated prices, and obtain explicit approval. No `azd up` or other automatic deployment during the planning-only phase. The runtime uses data access and inference permissions; the deployment identity has separate permissions.

Azure ML online endpoints and some data services have fixed costs. Define dev operating hours and selective compute cleanup while preserving data and audit records. Azure budgets do not automatically shut down resources.
