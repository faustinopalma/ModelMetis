# Reuse Decision And Current Blocker

Reuse the existing healthy resource in `rg-iveco-agent-testing-troubleshooting`; do not delete and recreate its resource group. The user explicitly authorized reuse or cleanup because its previous workload is no longer needed. The account already has Entra-only authentication and an inference role, whereas the newly created dedicated ModelMetis account remained Creating after more than an hour. Reusing the parent avoids another parent-resource creation. However, the attempt to add pinned GPT-5.6 Sol failed with an Azure `RequestConflict`, so no new model endpoint or successful inference is claimed.

The [machine-readable receipt](../ml/dsp-sol-reuse-status-v1.json) preserves the verified states. The previously submitted Global Standard quota request remains unchanged and will be reviewed on another day, as requested. This reuse path uses existing DataZoneStandard quota; it does not claim the requested Global Standard increase has been approved.

## Verified Inventory

The resource group contains one `Microsoft.CognitiveServices/accounts` resource, `aif-iveco-safety-test-20260918`, in Sweden Central, subscription `e2cb999b-d471-4148-9b22-1c4c8019cb4e`, tenant `937847db-d3f9-4c7b-9991-510e5c42f777`. No resource-group locks were returned. The parent provisioning state is Succeeded and local key authentication is disabled. Public network access is enabled; there is no verified IP-restricted firewall on this inherited resource. The existing Cognitive Services OpenAI User role is available at the resource scope. No keys were requested or printed.

| Existing deployment | Actual model/version | SKU | Capacity | State |
| --- | --- | --- | ---: | --- |
| gpt-56-terra-test | gpt-5.6-terra / 2026-07-09 | DataZoneStandard | 100 | Succeeded |
| gpt-51-test | gpt-5.1 / 2025-11-13 | DataZoneStandard | 100 | Succeeded |
| gpt-41-test | gpt-4.1 / 2025-04-14 | DataZoneStandard | 100 | Succeeded |
| gpt-56-luna-test | gpt-5.6-luna / 2026-07-09 | DataZoneStandard | 300 | Succeeded |

None is Sol. Their upgrade policy is OnceNewDefaultVersionAvailable, so they are not silently relabeled as the pinned Sol target. These four deployments and their parent were preserved. No existing workload allocation was removed to make the new test succeed. No group deletion, governance change or modification of Lanternina was performed.

## New Deployment Attempt

The [existing-account Bicep template](../infra/dsp-existing-account.bicep) declares the parent `existing` and creates only `modelmetis-dsp-sol`, OpenAI `gpt-5.6-sol@2026-07-09`, DataZoneStandard capacity 50, Microsoft.DefaultV2 and NoAutoUpgrade. Exact model/SKU availability was checked on the account; available DataZoneStandard Sol quota was 333 units before submission. Bicep compilation passed without diagnostics. ARM validation passed. The what-if was programmatically required to contain exactly one Create for that child and no other modifications or deletions before submission.

The ARM deployment `modelmetis-sol-reuse-20260929` was submitted once with `--no-wait`. An early child GET returned NotFound while ARM was still Running; no duplicate create was sent. The later terminal state was Failed after 2 minutes 20.747 seconds, with `RequestConflict`: "Another operation is being performed on the parent resource ... Please try again later." The parent remained Succeeded, and the new Sol child was absent. Correlation: `166e3970-9d60-4299-bb57-469ccc3bd082`.

The scoped activity-log inspection did not identify the conflicting parent operation. A Succeeded parent read does not prove that the internal operation lock has cleared. Do not delete this working resource as an unverified fix for that lock, and do not repeat creation indefinitely. Resolve or establish completion of the competing operation, then record any retry separately. Existing model inference has not been tested in this attempt, and no fallback from Sol to Terra/Luna was performed.

## Prepared Experiment

The [reuse settings](../configs/dsp-sol-reuse-v1.json) contain only endpoint metadata, public-price accounting and request limits. They point to the authorized IVECO parent, not the still-creating dedicated ModelMetis account. The [protocol](DSP_LLM_PROTOCOL.md) records the explicit target revision and inherited network posture. The old prepared registration remains immutable.

A fresh preparation is retained at `artifacts/dsp-sol-exp012-reuse-prepared-v1/`, hash `fe297154c5fb966d069df7fd399ce0523ae1f0481621159f884e692d4144af37`. It contains the same six original A/B source clips transformed into deterministic DSP evidence, twelve real jobs and one synthetic probe. Preparation took 29.604 seconds internally and 35.375 seconds including command overhead. Zero inference requests were submitted and inference consumption is zero. There is no diagnostic result, live token count or model latency to report.

Only after Sol actually exists with the required identity and policy should the bounded synthetic gate run. Keep the request/worker code and settings bound to the preparation; a necessary code change requires a new recorded preparation. Do not turn this infrastructure result into evidence for audio classification quality.

## Public Repository Protection

The user explicitly reiterated that credentials must not leak into the public repository. Azure caches, `.env` files other than examples, credential files, raw data, request payloads and contact receipts stay outside publication. Existing `.gitignore` coverage was checked for `.azure/azureProfile.json`, `.azure/msal_token_cache.bin`, `.azure/msal_http_cache.bin` and the submitted quota receipt; none is tracked. The inference worker captures the Azure CLI token into process memory, never inserts it into model request JSON, and does not print subprocess credential output.

The [publication checker](../scripts/check_publication.py) scans the complete current Git index, including newly staged files, and fails on excluded artifact paths or recognizable private keys, JWTs, GitHub tokens, storage account keys, SAS signatures and literal secret assignments. It prints only affected paths and pattern categories, never matched values. Synthetic negative controls verify rejection and redaction. Empty-index success is forbidden. Run it after staging and before commit/push:

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.check_publication | Out-Host }
```

This is a pattern-based guard for the current index, not proof that Git history or every possible secret format is clean. Subscription IDs, tenant IDs, resource names and HTTPS service endpoints are configuration identifiers, not bearer credentials. The public summaries do not include actual tokens, keys, execution IP addresses, or the quota requester's contact receipt. Existing unrelated dirty work remains outside the scoped commit.

## Preserved Attempts

Local logs include `dsp-iveco-reuse-inventory-v1.log` (23.488 s), `dsp-reuse-git-security-inventory-v1.log` (1.103 s), `dsp-reuse-readiness-v1.log` (22.036 s), `dsp-reuse-deployment-submit-v1.log` (62.328 s), early child readback (1.398 s, NotFound), running ARM read (2.806 s), final deployment readback (10.058 s, RequestConflict), conflict diagnosis (5.389 s), preparation (35.375 s), publication-test v1 (seven passing tests, two lint findings) and v2 (seven passing tests and clean lint; current-index scan returned no findings across 92 files). The terminal's verbose line redraw was not evidence of multiple Azure submissions. All artifacts and failed attempts remain local; no command was silently relabeled as a successful deployment.