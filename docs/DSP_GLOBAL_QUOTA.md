# Global Standard Quota Request: Submitted

Subsequent user instruction: leave this request for review on another day and [reuse the obsolete IVECO troubleshooting resource](DSP_RESOURCE_REUSE.md) if useful. The requested Global Standard increase was not rechecked or resubmitted during that work. Its approval remains unverified; the separate Data Zone reuse attempt does not establish a Global Standard quota change.

The GPT-5.6 Sol Global Standard quota increase request was **submitted successfully**, with confirmation observed on September 29, 2026 at 14:41:30 UTC. Customer Voice displayed "Thanks! You've completed the request!" and "Your response was submitted." Approval and increased quota are not yet verified; no Global Standard deployment retry has started. The existing Data Zone deployment operation was not modified or replayed.

The user requested this sequence on September 29, 2026: request more Global Standard quota first, then retry deployment. This supersedes the earlier plan to run EXP-012 through DataZoneStandard. Preserve that experiment's frozen settings and artifacts as history; do not execute the old Data Zone probe while the new target is unresolved.

## Requested Increase

| Field | Value |
| --- | --- |
| Subscription | `e2cb999b-d471-4148-9b22-1c4c8019cb4e` / ME-MngEnvMCAP872572-faustopalma-1 |
| Tenant | `937847db-d3f9-4c7b-9991-510e5c42f777` |
| Model | `gpt-5.6-sol`; intended deployment version `2026-07-09` |
| Deployment type | Global Standard |
| Preferred resource region | Sweden Central |
| Existing quota / allocation | 1,000 / 1,000 kTPM, fully allocated |
| Requested increment | 50 kTPM |
| Requested new total | **1,050 kTPM**, entered as `1050` in the official form |
| Planned ModelMetis allocation | 50 kTPM; existing workloads remain unchanged |
| Submission/approval | Submission confirmed; approval pending; no individual request ID displayed |

This requests capacity for a Microsoft Italia customer proof of concept, initially one synthetic probe and at most twelve sequential DSP reference-comparison calls. It does not claim that existing deployments are actively saturating their quota: only their allocation was measured. The published Microsoft guidance prioritizes workloads actually consuming their existing allocation, so approval is not guaranteed. No private spending allowance or credential is persisted.

## Verified Submission Route

The `quota` Azure CLI extension was installed into the existing CLI environment. `az quota list` against the Cognitive Services regional scope returned `BadRequest`; no `az quota update` was attempted against an unsupported provider. The [official Azure OpenAI quota documentation](https://learn.microsoft.com/azure/foundry/openai/how-to/quota#request-more-quota) directs requests to [Microsoft Foundry Service: Request for Quota Increase](https://aka.ms/oai/stuquotarequest).

The Customer Voice form was populated with the subscription, a factual customer-PoC justification, Model Deployment quota type, Azure OpenAI model type, Global Standard request type, `gpt-5.6-sol` and total quota `1050`. Selecting Sol hides the region field; Sweden Central remains explicitly stated in the justification. Microsoft Graph had returned null for all requester/company fields except the technical user principal name; the user subsequently supplied the required identity, email and company. The [official Microsoft office page](https://news.microsoft.com/it-it/dovesiamo/) confirmed Microsoft House, Viale Pasubio 21, 20154 Milano, Italy. All eight required fields were completed without inferred personal data.

The original unsubmitted draft remains in `artifacts/dsp-global-quota-request-v1.json`. The submitted fields, address source, justification and confirmation are preserved separately in `artifacts/dsp-global-quota-request-submitted-v2.json`; contact details remain in ignored local artifacts. Two standard browser clicks timed out in the stability check without dispatching an action. After verifying that the form was still present and the button visible/enabled, one DOM click on that same Submit button produced the explicit service confirmation; a subsequent read verified the form was absent. No duplicate submission was performed.

The confirmation page says requests are typically processed the next business day, sometimes up to two business days, and explicitly states that fulfillment is not guaranteed. It did not display an individual request ID. The shared form URL is not a request tracking identifier. Do not resubmit merely because a request ID was not shown.

## Separate Provisioning Issue

The quota check at 14:16:47 UTC showed Global Standard at 1,000/1,000 kTPM, DataZoneStandard at 0/333 kTPM, AIServices resource count 3/100 and regional resource count 3/200. The Data Zone attempt was still creating its parent resource after about 33 minutes, with no quota error on that operation. Thus the exhausted Global Standard model quota is real, but it does not explain the observed pre-model parent-resource delay in the Data Zone attempt.

The previously recorded governance diagnostic failure remains distinct: its target Log Analytics workspace does not exist, and its causal relationship to the parent-resource delay has not been established. Neither the quota request nor choosing Global Standard automatically repairs that issue. See the [packet/infrastructure handoff](DSP_LLM_FORMAT.md#azure-state) and [last saved readiness receipt](../ml/dsp-sol-exp012-status-v1.json). Obtain fresh ARM state before any further deployment action; do not overwrite a still-Running deployment.

## Resume Gates

1. Submission is complete; retain the successful confirmation and await the quota decision rather than sending a duplicate request.
2. Read the quota again after approval. An accepted submission is not an increased quota; require at least 50 kTPM actually available for Global Standard.
3. Check the current parent resource and existing deployment state. Diagnose unresolved Creating/Running or governance errors rather than blindly replaying the earlier operation.
4. Prepare a separately versioned Global Standard target/settings/registration with the correct public prices and scope. Do not silently edit the frozen Data Zone packet registration.
5. Validate/what-if the intended deployment, verify the live model/version and network/auth settings, then run the bounded synthetic gate before any real DSP comparisons.

No cloud deployment configuration or model inference request was changed during this quota-request attempt. The only local dependency change was installing the Azure CLI quota extension. Discovery took 1.987 seconds; extension installation/provider check 24.323 seconds; the limited Graph contact-field lookup 10.324 seconds. The Azure CLI command-generation helper reported this specialized quota request outside its scope, so the supported route was established from the official documentation and live form instead. Address lookup encountered obsolete Microsoft URLs, login redirects and search extraction failures; the rendered official office page ultimately supplied the verified address.