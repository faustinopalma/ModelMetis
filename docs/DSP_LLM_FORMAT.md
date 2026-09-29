# DSP Evidence Packets For Reference Comparison

Latest measured outcome: the user-authorized deployment retry succeeded, and the frozen reuse preparation was executed against `gpt-5.6-sol-2026-07-09`. [EXP-012 live results](DSP_LLM_RESULTS.md): 0/9 known trials recognized, 9/9 falsely rejected, 3/3 unknown trials rejected; no technical inference failures or retries. Total estimated consumption including the probe was USD 0.72875088. The readiness blockers below describe the earlier preserved attempts, not the current status of the reused Sol endpoint.

## Initial Preparation History

Initial infrastructure follow-up: the user authorized [reuse of the IVECO account](DSP_RESOURCE_REUSE.md) while the Global Standard quota request remains pending. The first Sol child creation failed with a parent RequestConflict; the existing models and resource group were preserved. The original preparation below is historical and unchanged; a separate reuse preparation was created. No successful model inference had occurred at this point.

Use a compact, typed evidence packet per reference/query interval: precise scalar DSP measurements plus two original images, FFT amplitude and STFT power density. This format is implemented, tested and instantiated on the six frozen drone A/B clips. Twelve stateless requests are prepared at 16-22 KB of text and at most 1.07 MB total per request, with six or eight images. The Azure resource creation was submitted, but the service was still provisioning at the latest documented check; no inference or diagnostic result is claimed until a live readiness/probe gate passes.

The [EXP-012 protocol](DSP_LLM_PROTOCOL.md) is the immutable experimental design. The [DSP generator](DSP_PIPELINE.md) remains purely analytical and does not call an LLM. Packaging, model invocation and sealed evaluation are separate modules. This is a first bounded packet format, not an empirically optimal image selection or a production classification service.

## Packet Contract

The [packet implementation](../src/modelmetis/dsp_packet.py) verifies the report manifest, evidence file, provenance binding and image hashes before constructing an input. Every image is the original metadata-free 1200 by 700 RGB PNG, not a screenshot of an HTML page or a thumbnail. The local packet preview is `artifacts/dsp-sol-exp012-prepared-v1/preview-v2.html`; it displays the same diagnostic text and eight PNGs as the first prepared request.

| Element | Sent to the model | Kept in the local audit |
| --- | --- | --- |
| Identity | R01/R02/R03 for references, Q01 for query; C01/C02/C03 for visible conditions | Original recording identity, physical group, source and PCM hashes, report manifest hash |
| Configuration | Common sample rate, interval length, FFT/STFT parameters, axes, scaling and units | Configuration/code/dependency hashes and environment versions |
| Measurements | RMS, peak, DC, crest factor, kurtosis, zero crossings, clipping/silence, FFT peaks, Welch density summary, band powers, envelope modulation and autocorrelation | Full numerical arrays and unrounded original report |
| Images | One original FFT plot, including its fixed 0-500 Hz detail; one original STFT plot; `detail=high` | PNG hashes, original report locations and source offsets |
| Quality/context | Unknown gain comparability, unverified regime homogeneity, declared prior signal processing and level-change candidate count | Query diagnoses, publisher source paths and evaluation truth |
| Output | Known condition, outside-reference or indeterminate; evidence citations and limitations | Raw response, usage, latency, parsed result and independent evaluator outcome |

Floats use seven significant digits, not a fixed number of decimal places: a small value such as `1.234568e-12` remains nonzero. Integer counts and null values remain exact. Original arrays and full precision are retained outside the prompt. The packet includes named units and nulls for undefined measurements; it does not translate digital full-scale units into sound-pressure levels or infer RPM/component geometry.

One packet covers one channel and one interval, not an entire long recording. A downstream long-recording workflow must preserve segment-level decisions and cannot turn a sampled overview or majority vote into evidence that every regime was inspected. EXP-012 uses half-second clips with one interval each. The four previous cross-dataset DSP demonstrations are not interchangeable reference classes; their hardware, processing and acquisition histories differ.

Before building a comparison, the implementation requires equal sampling rate, valid sample count, DSP configuration, generator/dependency versions, channel policy and declared source-processing history. Exact PCM duplicates are rejected. The experimental runner also checks that reference/query physical group IDs do not overlap. These are explicit checks, not proof that a caller's acquisition lineage is correct. A fresh microphone position, noise mixture or window index does not establish independence.

## Request Layout

The first text block contains the task, the complete visible condition/reference map, the query ID, shared configuration and units. Each subsequent packet contains a measurement ID and two image IDs. Text/image order is stable. A three-reference request uses eight images; a whole-condition holdout uses six. No previous model responses are included. The full HTML report, source provenance file, query truth and array archives are never copied into the request.

The following is a structural illustration; the generated request contains the actual measured values, original PNG data URLs and strict output schema:

```json
{
  "known_conditions": {"C01": "R01", "C02": "R02", "C03": "R03"},
  "query": "Q01",
  "packets": [
    {"id": "R01", "measurement_id": "R01.M01", "images": ["R01.I01", "R01.I02"]},
    {"id": "R02", "measurement_id": "R02.M01", "images": ["R02.I01", "R02.I02"]},
    {"id": "R03", "measurement_id": "R03.M01", "images": ["R03.I01", "R03.I02"]},
    {"id": "Q01", "measurement_id": "Q01.M01", "images": ["Q01.I01", "Q01.I02"]}
  ]
}
```

Required output fields are `outcome`, `condition_id`, `evidence_ids`, `explanation` and `limitations`. Azure strict structured output constrains the shape; local validation additionally checks that a known decision uses an actually visible condition, novelty/abstention uses null, and every cited evidence ID exists in this request. Refusals, truncated output, malformed JSON, fabricated citations, changed model identity and missing usage are distinct technical failures. An explanation or valid citation is not evidence of analytical correctness.

The exact model is `gpt-5.6-sol@2026-07-09`; no fallback to Luna, Terra, GPT Audio or another model is configured. Each request uses Chat Completions v1, low reasoning, at most 4,096 completion tokens including reasoning, strict JSON schema, no tools, no temperature parameter and no streaming. The [single-call worker](../src/modelmetis/dsp_inference.py) checks the live ARM model/version/SKU before acquiring a token and posting to the exact declared HTTPS endpoint. Credentials exist only in process memory and are never written into request/response files.

## Bounded Experiment

The [orchestrator](../scripts/dsp_experiment.py) creates a new immutable preparation directory and binds code, settings, jobs, source registration and sealed truth before sending anything. It reuses the existing three references and three queries from the EXP-011 A/B proxy and generates fresh deterministic DSP reports. No changes to EXP-011 artifacts or DSP code are required. One synthetic gate is permitted, followed by at most twelve real requests. A failed gate or first technical error stops the phase; there are no automatic retries. Each worker has a 180-second process deadline and each phase a 2,400-second scheduling deadline. A timed-out server call may still have executed; its cost/outcome stays unknown until reconciled, and it is not silently resubmitted.

Prepared registration: `dc94774abfc050044cccd60a40e9d67cbfa9d9e405e85ada8729d85b1a4c1c4b`. Text size ranges from 16,383 to 21,545 UTF-8 bytes; the largest complete JSON body is 1,064,263 bytes. Actual token counts require a provider response and are not inferred from byte counts. The first prepared body hash is `cc7761f3c9a3efa2664bc5a69a1ffcddd59dbe30b29c40897b5f9649ef3ea2f9`.

The public Data Zone Standard short-context prices consulted September 29 are USD 4.40 input, 0.44 cached input and 22 output per million tokens. The worker counts all completion tokens, including reasoning. Estimated cost is `(uncached_input * 4.40 + cached_input * 0.44 + completion * 22) / 1,000,000`; missing usage is not silently assigned zero. These are list-price estimates, not invoices or persisted private spending allowances. Source: https://azure.microsoft.com/en-us/pricing/details/azure-openai/.

## Azure State

The repo-local `.azure` credentials resolve to subscription `e2cb999b-d471-4148-9b22-1c4c8019cb4e`, tenant `937847db-d3f9-4c7b-9991-510e5c42f777`. The previous ModelMetis subscription `7ecf802f-04ac-4e81-8703-c3d39074f823` is not visible in that profile. Read-only discovery found no ModelMetis resources in the current subscription. Existing Lanternina and IVECO resources were excluded and not modified. The unrelated deployment plan in `.azure` was not reused.

Global Standard Sol quota is fully allocated in Sweden Central. DataZoneStandard showed 333 capacity/quota units available; the catalog reports 1,000 TPM and one RPM per unit. The user authorized autonomous decisions after the target/region/SKU confirmation prompt. The new dedicated RG `rg-modelmetis-dev-dsp-swc` was created and verified Succeeded. The [Bicep template](../infra/dsp-experiments.bicep) compiled with no diagnostics, passed ARM validation and produced a what-if with exactly three new resources: `aif-modelmetis-dsp-jxkma7rduph64`, its `modelmetis-dsp-sol` deployment, and a Cognitive Services OpenAI User role assignment scoped to the new resource.

The intended resource disables local key authentication, uses firewall default Deny with no bypass and one execution-machine IPv4 allow rule, and pins Sol with NoAutoUpgrade at DataZoneStandard capacity 50. There is no new storage, VM, hosted agent, provisioned-throughput allocation or shared-project modification. Credentials and the execution IP are not stored in this document.

The deployment command's local wait was cancelled after 321.040 seconds; this did not cancel ARM. Fresh reads showed the resource `Creating`, the deployment `Running`, no deployment-level error, and no model children at 16 minutes. At 19 minutes 48 seconds the same operation remained Running with correlation `e997e121-29fb-46bf-a727-656f4f9e5b92`. A separate automatic governance deployment, `PolicyDeployment_15917264444470485684`, failed: policy `CognitiveServices_Diagnostics_Enable` / `MCAPSGovDeployPolicies` attempted diagnostic settings whose destination `/resourcegroups/mcapsgovernance/providers/microsoft.operationalinsights/workspaces/mcaps41489b221c4c8019cb4e-la` does not exist. This is a confirmed governance error, not proof that it caused the primary resource's prolonged creation. No policy was disabled and no shared governance workspace was created to bypass the problem.

The [final readiness receipt](../ml/dsp-sol-exp012-status-v1.json), observed at 14:09:52 UTC, records the same Creating/Running state after 26 minutes 6.7 seconds, zero model deployments, twelve prepared real requests, one prepared probe and zero submitted inference requests. Inference consumption is zero; no classifier outcome, token usage or model latency was fabricated. The subsequent service outcome remains to be checked live.

Before inference, require fresh ARM Succeeded states for the resource and model, verify fixed identity/network configuration, and resolve the missing governance destination with its owner. Do not blindly replay the submitted deployment while it is still Running. The resource group and pending operation exist; a catalog entry, successful template validation or submitted deployment is not a live model endpoint. The exact latest state should be read again when resuming.

## Reproduction And Evidence

The native ARM64 environment is retained. No Azure SDK install or Python environment merge was required: the worker obtains a scoped Entra token through the existing CLI and uses installed HTTPX. A required Foundry dependency check failed while trying to install an azd extension because `azure.ai.agents` was missing; the verified direct CLI/REST/Bicep path does not depend on that extension, and azd was not upgraded.

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_experiment prepare --output artifacts/dsp-sol-exp012-prepared-replay | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.preview_dsp_packet --job artifacts/dsp-sol-exp012-prepared-replay/jobs/01.json --output artifacts/dsp-sol-exp012-prepared-replay/preview.html | Out-Host }
```

Only after Azure readiness and governance checks pass, the frozen probe and real phase can be executed. These commands deliberately refuse to overwrite an existing run; do not use a new output directory to evade a failed gate or request bound.

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_experiment probe --prepared artifacts/dsp-sol-exp012-prepared-v1 --output artifacts/dsp-sol-exp012-run-v1 | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_experiment run --prepared artifacts/dsp-sol-exp012-prepared-v1 --output artifacts/dsp-sol-exp012-run-v1 | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_experiment evaluate --prepared artifacts/dsp-sol-exp012-prepared-v1 --run artifacts/dsp-sol-exp012-run-v1 --output artifacts/dsp-sol-exp012-evaluation-v1 | Out-Host }
```

Do not alter frozen code/settings between preparation and execution. A necessary correction requires a separately documented preparation version and preserves every earlier request and response. The prepared folder, previews and local attempt logs remain ignored. Only reusable source, protocol, nonsecret deployment configuration and aggregate status are published. No accepted prediction is automatically inserted into a baseline, gold dataset, silver collection or training snapshot.

Validation reached 171 passing tests, Ruff clean and no editor diagnostics. Tests cover original image hashes, source-metadata exclusion, seven-digit numeric preservation, mismatch/duplicate rejection, output identity/citations and token accounting including reasoning. Browser checks confirmed all eight original PNGs load at 1200 by 700 with no horizontal overflow at 1440 or 390 pixels. This is local readability validation; effective provider preprocessing and vision interpretation remain unverified until a successful live probe, and a synthetic classification cannot establish acoustic diagnosis quality.

All command and failed-attempt logs are retained under `artifacts/dsp-*.log`: initial wrong-subscription lookup (3.262 s), scoped discovery (10.149 s), capacity checks (19.209, 11.022 and 10.097 s), ARM preflight (72.560 s), cancelled local deployment wait (321.040 s), readbacks (4.994 and 7.015 s), provisioning/policy diagnosis (7.034 and 4.646 s), preparation (30.657 s command / 26.719 s internal), packet test/format iterations, full test gate (26.999 s), and preview iterations (2.131 and 2.034 s). Windows `az.cmd` split a raw URL at `&`; using `--url-parameters` fixed it. Shell-sensitive JMESPath was replaced with structured PowerShell JSON selection. A settings serialization/hash mismatch was corrected before preparation. An interrupted test invocation was rerun; no inference was retried or hidden.