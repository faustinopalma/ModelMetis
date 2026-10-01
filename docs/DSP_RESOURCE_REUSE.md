# DSP Resource Reuse

**Pinned Sol deployment and inference succeeded; diagnostic comparison failed.** All twelve real queries were rejected, including 9/9 known-condition trials. [Results](DSP_LLM_RESULTS.md). The separate [Global Standard quota request](DSP_GLOBAL_QUOTA.md) remains unverified.

## Configuration

| Field | Value |
| --- | --- |
| Subscription / tenant | `e2cb999b-d471-4148-9b22-1c4c8019cb4e` / `937847db-d3f9-4c7b-9991-510e5c42f777` |
| Resource group | `rg-iveco-agent-testing-troubleshooting` |
| Foundry resource | `aif-iveco-safety-test-20260918`, Sweden Central |
| Added deployment | `modelmetis-dsp-sol`, `gpt-5.6-sol@2026-07-09` |
| Current SKU / capacity / upgrade | DataZoneStandard / 100 kTPM / NoAutoUpgrade |
| Authentication | Entra-only; resource-scoped Cognitive Services OpenAI User |
| Network | Public access enabled; no verified IP-restricted firewall on the inherited resource |

The existing Terra, Luna, GPT-5.1 and GPT-4.1 deployments were preserved. The [Bicep template](../infra/dsp-existing-account.bicep) declares the parent `existing` and creates only the Sol child. Compilation, ARM validation and an exact one-Create what-if passed. No resource group was deleted or governance policy changed.

The [all-diagram DSP experiment](DSP_EXTENSIONS.md) increased only the Sol capacity from 50 to 100 kTPM using this template with `capacity=100`, after quota and one-Modify what-if checks. ARM deployment `modelmetis-dsp-throughput-100` succeeded; a fresh read verified capacity 100 and the same pinned model/version/SKU. The historical preparations below remain bound to their original settings and receipts. The template default is still 50, so later deployments must pass the intended capacity explicitly.

## Attempts

The first deployment, `modelmetis-sol-reuse-20260929`, failed after 2 minutes 20.747 seconds with `RequestConflict`; the parent remained Succeeded and Sol was absent. The [receipt](../ml/dsp-sol-reuse-status-v1.json) preserves that state. The conflicting internal operation was not identified.

Before retry, fresh reads found a healthy parent, no Sol child and no active ARM deployment; available quota was rechecked. `modelmetis-sol-reuse-retry-20260929` succeeded in 5.499 seconds. One synthetic gate and twelve real calls then completed without inference retries.

The [reuse settings](../configs/dsp-sol-reuse-v1.json) bind the endpoint, model, public prices and limits. Preparation `artifacts/dsp-sol-exp012-reuse-prepared-v1/` has registration hash `fe297154c5fb966d069df7fd399ce0523ae1f0481621159f884e692d4144af37`. It preserves the six A/B clips and twelve-job schedule from the [protocol](DSP_LLM_PROTOCOL.md); original preparations remain unchanged.

## Publication Protection

Keep CLI caches, credentials, raw data, request/response bodies and contact receipts outside Git. Tokens remain in process memory and are excluded from payload files and logs. After staging, run:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_publication
```

The [checker](../scripts/check_publication.py) scans the full Git index for excluded paths and recognizable secrets, prints only paths/categories and rejects empty-index success. It does not audit Git history or guarantee detection of every secret format. Subscription/tenant IDs and endpoint names are configuration identifiers.
