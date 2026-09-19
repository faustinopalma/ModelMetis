# Azure Machine Learning Foundation

Status: draft, pending explicit infrastructure-plan and Bicep approval. Evidence collected September 18, 2026. No ModelMetis resource group, workspace, compute cluster, role assignment, or private endpoint has been created. A GPU quota request was submitted and declined. This document is the versioned handoff; it does not depend on ignored CLI state.

## Scope And Destination

Provide isolated specialist training, experiment tracking, artifact storage, and model registration. The local review application remains local-only. Foundry teacher deployment, public API hosting, PostgreSQL, Service Bus, production serving, and online endpoints are outside this increment. The learning and data-visibility requirements in [CONTEXT.md](CONTEXT.md) remain controlling.

| Setting | Proposed or verified value |
| --- | --- |
| Subscription, verified | `ME-MngEnvMCAP699805-faustopalma-1`, `7ecf802f-04ac-4e81-8703-c3d39074f823` |
| Tenant, verified | `39d764bc-ae80-46f9-b22c-6246cc5a20c2` |
| Region, proposed | `westeurope` |
| New resource group, proposed | `rg-modelmetis-dev-ml-weu` |
| IaC, proposed | Subscription-scope Bicep creates the new group; resource-group modules create its resources |
| Execution | Parameterized PowerShell locally; the same validation and deployment entry points from GitHub Actions or Azure DevOps later |

Live ARM authentication succeeded. The current identity has subscription Owner and inherited administrative roles. Discovery found no existing ModelMetis resource group. This does not reserve names or authorize reuse of other resources. Every Azure command must specify the subscription. Do not modify existing groups, policies, resources, or Lanternina. Do not register providers or grant subscription-wide CI roles without reviewing their effects.

## Resource Proposal

Names below are proposed, not reserved or deployed. Globally unique storage, registry, and vault names require a deterministic suffix and availability validation during IaC preparation. Tag new resources with project, environment, owner, and cost center; do not invent missing billing metadata.

| Component | Proposed configuration and reason |
| --- | --- |
| AML workspace | `mlw-modelmetis-dev-weu`; identity-based system datastores; public network access disabled; private endpoint; tracking and model registry, no serving endpoint |
| CPU cluster | `cpu-build`; Linux `Standard_DS3_v2`, dedicated, min 0/max 1; private image builds and initial CPU experiments; no node public IP or public SSH |
| GPU cluster | `gpu-t4`; Linux `Standard_NC4as_T4_v3`, dedicated, min 0/max 1; one T4 per node; no node public IP or public SSH |
| Optional larger GPU | `Standard_NC24ads_A100_v4`; excluded from initial deployment because West Europe AML quota is zero and the request failed |
| System/training storage | New `StorageV2` account, `Standard_LRS`; Blob and File private endpoints; shared-key authorization and public network access disabled; operational data and job artifacts only |
| Reference storage | Separate new `StorageV2` account, `Standard_LRS`; Blob private endpoint; shared-key authorization and public network access disabled; source mappings, publisher references, and held-out partitions outside default AML storage |
| Container registry | New Premium ACR, required for Private Link; public network access and admin access disabled; CPU image-build compute configured for private dependencies |
| Key Vault | New Standard vault, RBAC authorization, soft delete and purge protection; private endpoint; no embedded credentials |
| Network | New isolated VNet; separate compute and private-endpoint subnets; NSG and address ranges validated before generation; no peering or dependency on existing VNets |
| Outbound connectivity | One Standard NAT gateway and one Standard static IPv4 public IP on the compute subnet; outbound only, not a public management endpoint |
| Private endpoints | Six: workspace, ACR, vault, system Blob, system File, reference Blob; endpoint connection approval and DNS resolution must be verified |
| Private DNS | Blob, File, Key Vault, ACR, AML API and AML notebooks zones with links to the new VNet; validate exact names and zone groups against current schemas |
| Observability | New Log Analytics workspace and workspace-based Application Insights; configure retention and ingestion limits; no audio, labels, source paths, or secrets in telemetry |
| Identities | Distinct workspace/build, training, import, and evaluator identities; role scopes reviewed independently; CI deployment identity separate from runtime identities |

The initial clusters should return to zero after a short, parameterized idle interval. A one-node maximum bounds concurrency, not total spend: a stuck job can still run indefinitely. Job timeouts, experiment budgets, and recorded termination behavior are required before unattended training.

## Job Termination Contract

The September 18 local CLAP/specialist experiment used CPU only; no Azure job or GPU node was started. The user requested automatic GPU shutdown after work and offered later manual remediation as a fallback. That fallback does not replace automatic controls. The settings below are requirements for the pending IaC and orchestrator, not deployed or verified behavior.

- Set AML compute `min_instances: 0`, `max_instances: 1`, and `idle_time_before_scale_down: 120` seconds. Disable public SSH and node public IPs. Do not use a persistent compute instance or online endpoint for the batch experiment.
- Set each initial command job's `limits.timeout` to 1800 seconds. Expose it as a bounded parameter; increasing it requires an explicit experiment budget. Runtime timeout is not a queue/provisioning deadline.
- Apply an orchestration deadline of 45 minutes including provisioning, image setup and queue time. On success, failure, cancellation or deadline, execute finalization and cancel any still-running job owned by that run. Do not cancel another run or another project's compute.
- Record terminal job state and observe actual current node count returning to zero. The 120-second idle setting starts after work releases the node; it is not a guarantee that deallocation completes in 120 seconds. Keep a bounded ten-minute cleanup observation window; failure to reach zero must produce a failed cleanup status and an actionable resource identifier, not a successful report.
- Do not leave another queued job attached to the cluster while claiming that the run has shut down its GPU. Node maximum and minimum alone are not a spending cap. Successful cancellation is not proof of zero nodes.
- Test success, job failure and timeout paths with a small synthetic GPU job. Preserve job IDs, configuration, UTC start/end, final node counts and GPU availability evidence before running unattended work. Fixed ACR/network/storage costs continue after compute returns to zero.

Verified documentation: [AML compute YAML](https://learn.microsoft.com/azure/machine-learning/reference-yaml-compute-aml?view=azureml-api-2) and [command-job limits](https://learn.microsoft.com/azure/machine-learning/reference-yaml-job-command?view=azureml-api-2). No shutdown claim can be made until the private cluster and these paths have actually run.

## Networking Qualifications

NAT permits outbound connectivity; it is not an egress allowlist or proof of exfiltration containment. This proposal does not include a firewall. Private workspace/storage networking does not make Application Insights ingestion private; AMPLS is not included. Do not describe this design as fully private telemetry or a fully isolated outbound network. Adding those requirements changes the resource list and cost.

## Data And Identity Boundary

The workspace and training identities must have no reference-account role. Training inputs are sanitized audio and operational silver labels or authorized corrections, never publisher labels. Import can read publisher material and write sanitized objects; its source mappings stay restricted. The evaluator has read-only access to the appropriate held-out partition and frozen candidates, and no training-write or promotion authority. Development and final-gold access must remain separately scoped even within reference storage. Broad account-level rights must not erase that separation.

Use `systemDatastoresAuthMode: 'identity'` with the documented role assignments before disabling storage keys; disabling keys alone is not a working AML configuration. Validate Blob and File requirements independently. No compute instance is planned. Private image builds must use the CPU cluster and an identity permitted to push images; training needs pull and explicitly scoped data access, not deployment privileges. Administrator permissions are outside the runtime-isolation guarantee: subscription Owners can change access controls.

## Quota And Policy Evidence

Source: the provider-specific AML regional `usages` API, API version `2024-10-01`, queried September 18. These are AML quotas, not `Microsoft.Compute` quotas. All listed dedicated usage values were zero.

| AML quota | West Europe limit | Italy North limit |
| --- | ---: | ---: |
| Total dedicated vCPUs | 1016 | 140 |
| DSv2 family vCPUs | 100 | 0 |
| DSv3 family vCPUs | 100 | 0 |
| NCASv3 T4 family vCPUs | 16 | 16 |
| NCADSA100v4 family vCPUs | 0 | 24 |

West Europe permits the proposed four-vCPU CPU and four-vCPU T4 clusters within current quota. Italy North already has A100 quota but the inspected dedicated CPU families have zero quota. No second regional environment is proposed. Regional VM-size listing was verified for Italy North; West Europe `vmSizes` availability still needs verification before generation. Neither quota nor a listed SKU guarantees physical capacity or successful scale-up.

The authorized request for 24 dedicated AML A100 vCPUs in West Europe was submitted at `2026-09-18T08:41:01Z`. Request ID: `1bdc471e-ce36-46a2-a266-b0757a88c386`. Final service state: `Failed`; error: `QuotaNotAvailableForResource`. A separate AML usage read confirmed the limit remained zero. The API did not provide a more specific reason. Do not report this as approved, pending, or a hardware-capacity diagnosis.

Prepared justification for a support escalation: "I am a Cloud Solution Architect building customer proofs of concept and demonstrations that require GPU compute." The submitted `az quota update` request had no free-text justification field, so this text was not transmitted with that request. No support ticket has been opened. A100 is optional; do not resubmit the same request repeatedly or block initial T4 work on its approval.

The inherited `VirtualMachine_SKU_Deny` rule inspected targets `Microsoft.Compute/virtualMachines` and `Microsoft.Compute/virtualMachineScaleSets`, includes T4/A100 sizes, and exempts Spot priority. It does not directly match `Microsoft.MachineLearningServices/workspaces/computes`. This is not proof that an AML scale-up will succeed under all inherited policies. Do not bypass, modify, or exempt the policy. What-if and a real bounded scale-up remain necessary. The assignment displayed as "Block Azure RM Resource Creation" inspected here restricts classic resource types; its title alone must not be treated as a blanket ARM prohibition. Storage must remain private regardless of whether the exact inherited storage-enforcement rule has been fully traced.

Discovery encountered two tooling limitations: the generic quota script failed parsing its response, and `az ml compute list-sizes` required an existing workspace. Provider-specific `usages` and regional `vmSizes` REST reads supplied usable evidence without reusing another project's workspace. Generic quota records with `isQuotaApplicable: false` and limit `-1` are not evidence of unlimited capacity.

## Cost Estimate

Public USD consumption prices retrieved September 18, 2026 through Azure Retail Prices and the Azure pricing tool. Use 730 hours and 730/24 days per month. West Europe meters apply to registry, public IP and VM compute; Private Link and NAT are indexed as Global. These are list-price estimates, not the subscription's negotiated bill, taxes, credits, reservations, or a spending cap.

| Fixed component | Price and quantity | Monthly USD |
| --- | --- | ---: |
| ACR Premium Registry Unit | 1.6666/day, one registry | 50.69 |
| Standard NAT Gateway | 0.045/hour, one gateway | 32.85 |
| Standard static IPv4 public IP | 0.005/hour, one address | 3.65 |
| Standard Private Endpoint | 0.01/hour, six endpoints | 43.80 |
| Verified fixed subtotal | Excludes the variable and unpriced items below | 130.99 |

| Compute or usage item | Verified rate |
| --- | --- |
| Linux DS3 v2, dedicated/on-demand VM meter | 0.272 USD/node-hour |
| Linux NC4as T4 v3, dedicated/on-demand VM meter | 0.658 USD/node-hour |
| NAT data processed | 0.045 USD/GB |

For illustration, 20 CPU node-hours and 20 T4 node-hours add 18.60 USD to the fixed subtotal, before all other charges. Provisioning, image builds and idle nodes before scale-down consume billable time too. A100 is excluded; its West Europe price has not been included in this estimate.

Private DNS, storage capacity/transactions, File shares, disks, registry storage over the included allowance, private-endpoint data processing, bandwidth, Key Vault operations, and log ingestion/retention are additional. The first DNS pricing lookup returned no records and is not evidence of a zero price. The previously discussed 120-160 USD/month range was preliminary; the verified fixed subtotal is already about 131 USD/month before these additions. Use that subtotal plus explicit usage allowances for approval, not the bottom of the preliminary range. Minimum-zero compute does not remove these fixed costs. Budgets and alerts do not automatically stop spending.

## Automation And Private Access

After approval, generate Bicep modules under `infra/`, environment parameters without secrets, and reusable validation/deployment scripts. Validate the caller's subscription and all target names; fail on a wrong destination. Perform a first-deployment collision check so an existing resource is not silently adopted. Subsequent deployments must verify that the resources belong to this ModelMetis environment.

Use federated OIDC for future pipeline authentication. Infrastructure validation and ARM deployment can run through the public management plane; this does not grant public access to private data. A public GitHub or Azure DevOps runner cannot directly upload code/data to the private workspace storage, push images to private ACR, or access the private AML data plane. Azure ML Studio from an off-VNet browser is similarly constrained. A dedicated private runner or authenticated VNet-connected job path must be selected, costed and authorized before claiming end-to-end pipeline support. No existing Lanternina access path may be reused. No runner, VPN, jump host, or public upload service has yet been included or deployed.

Validate current resource schemas, API versions, providers, region/SKU support, DNS, RBAC and policy effects before deployment. The what-if review must reject modifications or deletions outside the dedicated target and unexpected changes within it. Use incremental deployment, not complete-mode deletion. Restrict cleanup to verified ModelMetis-owned resources and obtain approval before deletion; preserve audit data and account for Key Vault purge protection.

## Next Actions And Acceptance

1. Obtain explicit approval for the resource list, the fixed subtotal plus usage allowances, and Bicep generation. General resource-creation authorization exists, but the exact-plan question did not receive an explicit approval; the user was unavailable. No cost-bearing resource creation followed.
2. Resolve the private execution/access path, remaining prices, West Europe VM-size availability, full applicable policy checks, exact schemas, and least-privilege role matrix. Keep the failed A100 request optional; a support escalation needs the brief justification above and any required factual contact details.
3. Generate Bicep and parameterized scripts. Immediately build/lint the touched templates; validate parameters, permissions and scope; obtain an ARM what-if preview. Do not treat a successful compile as evidence that private datastore access works.
4. Present the validated destination, cost and risks and obtain the required deployment approval. Deploy only dedicated ModelMetis resources. Record deployment outputs, IDs, region and exact commands without secrets.
5. Verify positive and negative boundaries with nonempty synthetic test data: authorized private read/write succeeds; public data-plane access fails; training cannot read reference storage; evaluator cannot write training data. Verify keys/public access remain disabled and DNS resolves to private addresses from the execution environment.
6. Run bounded CPU and T4 smoke jobs, including a private image build; verify expected artifacts, identity use, exit status, wall time and return to zero nodes. A cluster existing at zero nodes is not evidence of runnable GPU capacity. No real publisher data or gold labels are required for this smoke test.
7. Record evidence and remaining gaps in [CONTEXT.md](CONTEXT.md). The local source audit and CLAP/silver specialist evaluation are now recorded in the [ML experiment](../ml/README.md); their negative diagnostic result does not establish a competent LLM teacher or cloud execution readiness.

## Sources

- [AML quotas and limits](https://learn.microsoft.com/azure/machine-learning/how-to-manage-quotas?view=azureml-api-2)
- [Disable local authentication for AML storage](https://learn.microsoft.com/azure/machine-learning/how-to-disable-local-auth-storage)
- [Identity-based service authentication](https://learn.microsoft.com/azure/machine-learning/how-to-identity-based-service-authentication)
- [Secure workspace and dependencies](https://learn.microsoft.com/azure/machine-learning/how-to-secure-workspace-vnet)
- [Secure training environments](https://learn.microsoft.com/azure/machine-learning/how-to-secure-training-vnet?view=azureml-api-2)
- [Network isolation with CLI and SDK v2](https://learn.microsoft.com/azure/machine-learning/how-to-configure-network-isolation-with-v2)
- [AML Well-Architected service guide](https://learn.microsoft.com/azure/well-architected/service-guides/azure-machine-learning)
- [Blob Storage Well-Architected service guide](https://learn.microsoft.com/azure/well-architected/service-guides/azure-blob-storage)
- [Azure resource naming rules](https://learn.microsoft.com/azure/azure-resource-manager/management/resource-name-rules)
- [Azure Retail Prices API](https://prices.azure.com/api/retail/prices)
