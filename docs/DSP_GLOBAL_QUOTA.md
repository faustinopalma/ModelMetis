# Global Standard Quota

**The GPT-5.6 Sol quota increase was submitted; approval and increased capacity remain unverified.** No Global Standard deployment retry occurred. The completed [DataZoneStandard reuse experiment](DSP_RESOURCE_REUSE.md) is independent of this request.

## Requested Increase

| Field | Value |
| --- | --- |
| Subscription | `e2cb999b-d471-4148-9b22-1c4c8019cb4e` |
| Tenant | `937847db-d3f9-4c7b-9991-510e5c42f777` |
| Model/version | `gpt-5.6-sol@2026-07-09` |
| Deployment type / preferred region | Global Standard / Sweden Central |
| Quota / allocation at inspection | 1,000 / 1,000 kTPM |
| Requested total / increment | 1,050 / 50 kTPM |
| Submission | Confirmed; no individual request ID displayed |

The request supports a Microsoft Italia customer PoC and preserves existing allocations. Full allocation does not establish active consumption or guarantee approval.

## Submission Evidence

The Cognitive Services `az quota list` call returned `BadRequest`. The [official quota documentation](https://learn.microsoft.com/azure/foundry/openai/how-to/quota#request-more-quota) directs requests to the [Foundry quota form](https://aka.ms/oai/stuquotarequest). The form confirmed submission with "Your response was submitted." Sol selection hid the region field, so Sweden Central was included in the justification.

The receipt is retained at ignored `artifacts/dsp-global-quota-request-submitted-v2.json`; contact details are excluded from publication. Absence of a request ID does not justify resubmission.

## Resume Gates

1. Verify approval and at least 50 kTPM available Global Standard quota.
2. Read current resource/deployment state before further operations. The original dedicated parent delay had no model-quota error; the missing governance diagnostic destination is a separate unresolved issue. [Saved readiness receipt](../ml/dsp-sol-exp012-status-v1.json).
3. Create a separately versioned Global Standard configuration and registration with current prices. Preserve the frozen Data Zone preparations.
4. Validate the deployment change set, live model/version and security settings before a bounded synthetic gate and any new real comparison.
