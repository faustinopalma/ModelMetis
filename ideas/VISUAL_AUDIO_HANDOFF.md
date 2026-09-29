# Visual Audio Comparison: Session Handoff

Latest retry completed: [EXP-012 live results](../docs/DSP_LLM_RESULTS.md). Sol was deployed successfully on the reused IVECO resource and returned valid responses to one synthetic and twelve real requests. All twelve real outcomes were outside-reference: 9/9 known trials were falsely rejected and 3/3 unknown trials correctly rejected. Cost including probe USD 0.72875088, no inference retries, no promotion or further search. The earlier credential-checked commit 15f85c9 was pushed after DNS recovered. Leave the submitted Global Standard quota request for later; do not repeat the completed experiment or treat this negative outcome as useful recognition.

Previous attempt, preserved as history: [reuse the IVECO troubleshooting account](../docs/DSP_RESOURCE_REUSE.md) while leaving the submitted Global Standard quota request for another day. The parent was healthy; its existing models were not Sol. The first attempt to add pinned Sol DataZoneStandard failed with RequestConflict on the parent, with no child created; no group was deleted and no model was substituted. A fresh reuse preparation was retained, with zero inference calls at that stage. The later successful retry and its negative results are recorded above. Credential caches/contact receipts remain ignored, and the Git-index publication guard must pass before any public commit/push.

Latest user instruction: request more GPT-5.6 Sol **Global Standard** quota before retrying deployment. The [quota-request handoff](../docs/DSP_GLOBAL_QUOTA.md) records the **successful submission**, confirmed September 29 at 14:41:30 UTC, for 1,050 kTPM total (50 kTPM additional) for a Microsoft Italia customer PoC. Approval is pending; no individual request ID was displayed. Do not resubmit or run the earlier Data Zone probe, and do not mutate its frozen registration. Require actual quota approval/availability and a fresh provisioning-state check before the Global Standard retry.

Latest September 29 direction: [compact DSP-to-LLM evidence format](../docs/DSP_LLM_FORMAT.md) and [EXP-012 protocol](../docs/DSP_LLM_PROTOCOL.md). Exact FFT/STFT images plus typed DSP measurements are prepared for GPT-5.6 Sol. The user authorized dedicated resources in the repo-local Azure subscription; creation was submitted, but a fresh readiness check and resolution of the recorded missing governance diagnostic destination are required before inference. The six A/B source clips and all twelve requests are frozen; C remains excluded. Do not confuse submitted infrastructure or prepared requests with a completed model experiment.

Current priority after the September 29 user review: build and inspect the [deterministic multiview DSP reporting pipeline](../docs/DSP_PIPELINE.md), including FFT, before any further model experiment. Reports were generated from drone, the complete 600-second Jin recording, AI Mechanic and Ottawa: 67 images, 125 measured intervals, zero LLM calls, 165 passing tests and clean Ruff. This new reporting task permits complementary analytical views; it does not retroactively alter EXP-011's STFT-only restriction or frozen evidence.

September 29 implementation update: [EXP-011 protocol and reproduction](../docs/VISUAL_AUDIO_EXPERIMENT.md) and [results and blocker](../docs/VISUAL_AUDIO_RESULTS.md). The STFT-only offline tool is verified (152 full-suite tests pass); the real-data Welch control abstained on 12/12 trials. No visual inference ran because no GPT-5.6 deployment was available in the authorized resource. Only STFT images are permitted in this experiment; all alternative visual representations below are superseded by the user's implementation-session constraint. No C access, silver collection, training or routing followed. The remainder preserves the original handoff.

Prepared September 29, 2026. Start here for the next implementation session, in the existing ModelMetis workspace. This is a staged work specification, not a frozen experimental registration or a positive result. No visual-audio model experiment has run. The first deliverable is a bounded feasibility experiment, not a production system or a training service.

## Objective

Turn audio into reproducible images and compare a new segment with a small reference set representing several known conditions. A condition can describe an operating regime, a verified fault, or another explicitly defined state. The multimodal model must return one known condition, outside-reference, or indeterminate. Do not force a nearest-condition answer. Outside-reference does not establish a mechanical fault, and a known condition need not be healthy.

Use one confirmed recording per condition initially, as previously requested. Multiple views or windows from one recording are not independent examples or new human diagnoses. Additional ordinary human labeling is not an acceptable way to rescue a weak result. Automatic predictions remain silver; only confirmed diagnoses become gold. Publisher annotations may simulate the initial human references, with explicit provenance, while query answers stay sealed to the evaluator.

## Work In Three Parts

1. **Next session: minimum renderer, comparison runner and feasibility experiment.** Build only what is required to test the hypothesis end to end: validated audio decoding, traceable automatic windows, deterministic images, a fixed reference package, one real multimodal candidate including GPT-5.6 in model selection, a simple numerical comparison and isolated evaluation. Record all failures and the final go/no-go/inconclusive verdict. A successful API call is not a successful method.
2. **Only after a useful signal: regime segmentation and robust operation.** Test label-blind change-point detection on real recordings containing multiple regimes, define mixed/transition handling, and make the runner resumable and operationally bounded. Confirm the chosen method on genuinely independent acquisitions; keep cross-machine transfer separate from within-machine feasibility. Do not open the protected C set without explicit authorization and a new frozen protocol.
3. **Only after adequate teacher quality: silver collection and specialists.** Convert accepted operational decisions into versioned training candidates, then test cheaper specialists against independent references and the teacher. Do not build automatic retraining, routing or promotion before the underlying comparison works.

Stop between stages to report measured evidence. A negative first experiment is a completed deliverable; do not automatically increase the number of human references or try an unlimited sequence of prompts, models and representations.

## Part 1: Audio To Images

Provide a reusable local tool or CLI that takes an audio file or masked manifest plus a versioned rendering configuration. Reuse the existing loaders and provenance patterns where suitable; inspect the owning implementation before changing it. Keep new experiment code separate from hash-bound historical runners.

- Decode by content, not only extension; existing drone files include FLAC under WAV names. Validate duration, sample rate, channels, finite samples, silence, clipping and incomplete input. Do not silently downmix, normalize, resample or discard data. Record every selected transformation and rejection.
- Automatically divide long files into bounded analysis windows with explicit parent recording ID, sample offsets, start/end seconds and channel policy. Choose window duration and overlap from the actual signal and desired frequency/time resolution before inference. A short file may remain one window; no repetition or unrelated concatenation to manufacture duration. Declare tail and padding behavior, including valid duration.
- All windows from an original acquisition, microphone pair, augmentation or duplicate belong to the same split. Split physical units and original recordings before creating windows. Unknown acquisition lineage remains a limitation, not a new inferred independence claim.
- Fixed windows are a minimum implementation, not proof of homogeneous regimes. A window may cross a transition. Preserve it as mixed/indeterminate or flag a candidate boundary using a frozen label-blind rule; never choose boundaries from query diagnoses or model success. Do not silently select only easy stable windows.
- Start with a log-power STFT spectrogram, with linear frequency axis and explicit physical units, plus a Welch power spectrum as a separate optional representation. Freeze sample rate, channel rule, window function, FFT length, hop, frequency range, reference power, dB limits, image size, axes and colormap. Match these between references and queries.
- Do not autoscale each image's colors or normalize each segment's peak independently: either can conceal amplitude changes. If gain normalization is necessary, preregister it as a distinct configuration, retain original level measurements, and do not claim calibrated sound pressure without calibration.
- Produce lossless PNGs and a machine-readable manifest binding source PCM hash, parent identity, offsets, configuration/code versions and image hashes. The model sees neutral reference identifiers and allowed context only, not source names, paths, answer-bearing titles, query labels or evaluation metadata.
- Verify the actual PNGs and the model's configured resizing/detail behavior. A valid file that becomes unreadable after resizing is not a valid rendering pipeline. Cache references by content/configuration hash; a changed renderer creates a new reference version.

For a file containing several conditions, return segment-level decisions and a time-indexed summary. Do not assign one forced condition to the whole file or let majority voting erase a short abnormal interval. Any file-level alert aggregation must be frozen and evaluated separately.

### Representation Options

| Representation | What it exposes | Main limitation / decision |
| --- | --- | --- |
| STFT power spectrogram in dB | Frequency content over time: harmonics, transients and sustained bands | First candidate; time/frequency resolution trade-off must match clip duration |
| Welch power spectral density | Stable peaks, harmonics and broadband energy averaged over a segment | First simple numerical control and optional visual ablation; loses timing |
| Mel spectrogram | A compact time-frequency view weighted toward auditory frequency resolution | Possible later ablation; can merge narrow mechanical components |
| Constant-Q or log-frequency view | Relative frequency structure over a wide frequency range | Does not by itself compensate for changing rotational speed |
| Wavelet scalogram | Transients at several time scales | More configuration and rendering choices; justify before adding |
| Envelope spectrum | Periodicity of amplitude modulation in a selected band | Requires a justified analysis band and adequate duration/sample rate; not a universal fault detector |
| Order spectrum / order map | Components expressed relative to shaft rotational speed | Requires reliable RPM/tachometer information and appropriate resampling; do not infer RPM from the hidden fault label |
| Waveform and RMS trend | Silence, clipping, gross level changes and candidate transitions | Quality/segmentation aid, not sufficient evidence of fault identity |

Do not send every representation by default or search them all against evaluation answers. For the first bounded screen, choose one primary view; freeze any additional view as a separate small ablation. More images from the same sound add views, not independent evidence.

## Part 1: Model Comparison Contract

Send the reference images and the query image(s) together. Each reference has an opaque condition ID and an explicitly authorized condition description if useful; the query has no diagnostic metadata. The supplied reference set is the complete set of allowed known IDs for that request. Baseline version, image order, rendering, prompt, model version and inference settings are immutable during an evaluated run.

Use a strict structured result with three outcomes:

- `known`: exactly one condition ID from the supplied reference set, plus a concise description of observed similarities/differences.
- `outside_reference`: no known ID, with observed differences from the supplied references. This is a novelty candidate, not a new diagnosis or a gold label.
- `indeterminate`: no known ID, with a reason such as incompatible acquisition, insufficient resolution, mixed state or ambiguity between references.

Reject malformed outputs, IDs absent from the current reference set and inconsistent combinations. Keep transport/parser failures distinct from model abstentions and include both in total workload and coverage accounting. Model explanations and self-reported confidence are not calibrated correctness. Do not automatically repair responses or hide retries.

Include GPT-5.6 in the candidate assessment, but verify the exact provider model ID, version, image-input support, detail/resizing behavior, structured-output support, access and actual limits in the implementation session. Earlier conversation claims about model variants and API image counts are not a verified deployment. Do not silently fall back to another model. A small synthetic two-image probe verifies transport/format only, not acoustic feasibility. Reuse authorized infrastructure only after checking compatibility; do not repurpose the unrelated workspace `.azure` or provision resources without the applicable authorization.

The rendering tool calculates plots from the signal; it must not use a generative image model. The operational path can be a deterministic pipeline and does not require an agent to decide when to render.

## Part 1: Experiment And Decision

Before real model calls, register the next unused experiment ID (expected EXP-011; verify), the hypothesis, dataset, source rights, acquisition groups, condition definitions, exact support selection, split, all renderer parameters, model/prompt version, numerical baseline, request/deadline limits, metrics and stop rules. Hash and retain the registration. Current numeric error/coverage/human-effort targets are not agreed; obtain those decisions for a feasibility verdict, or explicitly label a bounded run exploratory with no promotion claim. Never invent an acceptable error rate after observing results.

1. **Choose suitable data before coding dataset assumptions.** Prefer comparable recordings within a controlled family for this first question. Inspect real duration, sampling, regimes, rights and acquisition lineage. Existing material is available locally but already-consumed development data is not fresh confirmation. Half-second drone clips cannot validate long-file regime segmentation. If no suitable independent recordings exist, report that limitation and request the specific recordings/physical verification needed; do not fabricate evidence.
2. **Keep two separate evaluation questions.** For known-condition recognition, query new acquisitions of conditions present in the references. For novelty, leave an entire condition out of all model-visible references and descriptions, and query that excluded condition as well as retained known conditions. Balance/declare reference-set sizes and freeze the omitted-condition schedule. Withholding one recording while leaving its condition represented is not an unknown-condition test.
3. **Prevent leakage across folds and time.** Use fresh stateless requests without previous query answers or reference sets. Do not mix siblings of one recording across support, selection and evaluation. Freeze any numerical distance thresholds using a separate permitted selection source, not evaluation answers; no hidden extra operational labels. Whole-condition holdouts in an already-consumed dataset are useful exploratory evidence, not a fresh blind population test.
4. **Use a simple numerical control.** Compare normalized/log-Welch or equivalent fixed spectral features against the same references with a preregistered distance/rejection rule. Share query selection and information allowances with the visual method. Report unknown false acceptance as well as known recognition; a nearest-reference classifier without rejection is not an equivalent open-set control. A numerical method may be the useful outcome if the visual model adds no benefit.
5. **Measure the real errors.** Report correct known assignments, known-to-wrong-known errors, known false rejections, unknown-to-known false acceptance, unknown rejection, indeterminate and technical failure counts. Give explicit denominators, a confusion table including unknown, accepted-label error and coverage, and performance by condition/regime. Zero accepted cases is not zero-error success. Rejection of everything is not useful novelty detection. Count independent recordings/units, not correlated windows; use acquisition-level uncertainty where support permits it and disclose small-sample limits.
6. **Account for operation.** Measure end-to-end and model latency, image/token counts, estimated inference costs with price provenance, and human reference/calibration/correction/audit effort. False alerts per operating hour require real recording duration and a frozen event aggregation rule; do not infer them from a balanced collection of short clips. Do not persist private spending allowances or secrets.
7. **Conclude and stop.** Retain all attempted configurations, technical failures and negative outcomes, and compare against the numerical control. Report success only against prespecified goals; otherwise failure, inconclusive or promising-but-unconfirmed. Do not select the nicest examples or expand the search silently. No automatic production release, silver expansion or specialist training at this gate.

## Part 2: Regime Segmentation

After the minimum test, evaluate whether automatic change-point detection improves decisions on genuinely multi-regime recordings. Use short-time energy and spectral features without fault labels, and an established implementation where appropriate. Freeze smoothing, minimum segment duration, thresholds, boundary handling and maximum segment/request counts. Keep a fixed-window baseline. Silence/VAD is not a general detector of operating regimes, and acoustic boundaries are not diagnoses.

Verify no-change signals, speed/load transitions, short events, silence, noise, clipping and file tails. Synthetic signals validate mechanics only; real multi-regime acquisitions with independently checked boundaries are needed for the operational claim. Measure boundary errors/oversegmentation and their effect on downstream errors, coverage and model calls. If physical recordings are required, ask the user for them rather than assuming access. Do not require exhaustive human labeling of every window.

## Part 3: Silver Dataset And Specialists

From Part 1 onward, retain immutable experiment predictions with sufficient provenance to avoid rerunning calls. That audit log is not automatically an eligible training dataset. Once the teacher passes the relevant gate, add the collection/export mechanism using the existing silver-only learning contracts where compatible.

Each candidate training record needs parent audio/hash, segment offsets, recording/unit group, image/configuration hashes, reference-set/taxonomy version, prompt hash, actual provider/model version, parsed decision, provenance, timestamp and review status. Separate unreviewed accepted silver, confirmed gold, unresolved novelty, indeterminate input and technical failure. Outside-reference is not a single physical fault class; do not train it as one by default.

Never add the teacher's automatic answers to the gold reference set. Version and validate occasional human-confirmed additions; retain the original decision before review and corrections as separate events. Deduplicate/limit overlapping windows and keep all siblings in one partition. Keep evaluation recordings and their labels out of training even when the teacher classified them. A reviewed representative does not verify an entire cluster.

Train cheaper specialists only from eligible training partitions and explicit snapshots; the student's input may be audio or numerical features, not necessarily the rendered images. Evaluate on independent truth, including unknown-condition rejection, and compare quality/coverage/latency/full cost with the teacher. Teacher/student agreement is not accuracy. Routing, online updates and promotion remain conditional on those results.

## Starting State And Local Evidence

Verified September 29, 2026: branch `main`; HEAD `451b672b9301167b5919eda15162834c455fc44d` (`Publish negative audio-teacher results and reproducible experiments`); working tree contains substantial uncommitted experimental, documentation, console and infrastructure work. This handoff targets the same workspace, not a clean clone of HEAD. Do not reset, clean, broadly stage or commit those changes. A separate documentation-only commit will contain this handoff; inspect Git for its exact ID.

Local data directories checked present: `data/drone-source-v1`, `data/drone-one-shot-v1`, `data/jin-directions-v1`, `data/mechanic-one-shot-v1`, `data/mechanic-simulation-v1`, `data/ottawa-simulation-v1`, `data/raw` and `data/encoder-models`. Presence is not renewed content/hash verification. Existing artifacts and datasets must not be overwritten. C has no recorded model access; do not open it for the new method.

The documented runtimes are the native Windows ARM64 application environment `.venv/Scripts/python.exe` and the separate emulated x64 ML environment `data/ml-runtime/Scripts/python.exe`. Historical Python version is 3.13.13 in both. Do not merge them or upgrade existing ML packages speculatively. The application declares Python >=3.12, Ruff line length 100, and pytest under `tests`. Verify current interpreter/package state before selecting rendering dependencies. GPU work is not needed to calculate these images.

Last recorded full software verification, September 19: 120 tests passed in 10.49 seconds, no skips; Ruff passed; three dependency warnings. This is historical, not a September 29 rerun. Before implementation, establish a current baseline with `.venv/Scripts/python.exe -m pytest -q` and `.venv/Scripts/python.exe -m ruff check src scripts tests`, timing both and preserving unrelated failures.

Evidence that determines this next step: EXP-009 used nine supports and 54 cross-drone queries; all tested geometric rejection policies had zero coverage. EXP-010 compared five encoders; Dasheng-1.2B reached 18/54 same-condition nearest neighbors and 74/270 same-condition top-five links, but only 90/751 within-cluster pairs shared a condition under the fixed clustering protocol. These are negative/limited proxy results, not heavy-vehicle validation. No visual comparison has been evaluated, and no model is promoted.

## Files To Read Selectively

- [Working context](../docs/CONTEXT.md): requirements, latest state, data boundaries and historical environment problems.
- [Experiment record](../docs/EXPERIMENTS.md): preserve EXP-001 through EXP-010 and all failures; EXP-003 used textual spectral measurements with audio, not this visual reference-set experiment.
- [Sparse-annotation contract](../docs/ADAPTIVE_MODELS.md#sparse-human-annotation-contract): gold/silver distinction, occasional review and refusal to grow routine human labeling.
- [Dataset audit](../docs/AUDIO_DATASETS.md): rights, physical grouping, confounds and duration limitations.
- [Automation guide](../scripts/README.md): existing immutable runs, loaders, separated evaluator, request ledgers and reproduction commands.
- [Audio primitives](../src/modelmetis/audio.py), [audio teacher](../src/modelmetis/audio_teacher.py), [simulation and training](../src/modelmetis/simulation.py), [learning tests](../tests/test_learning.py): potential reuse points, not authorization to alter frozen historical behavior.
- [Dependency configuration](../pyproject.toml) and [ML runtime pins](../ml/requirements-encoder-windows-x64.txt): inspect before installing anything.
- [Backlog](../docs/BACKLOG.md#deferred-video-task): MM-021 remains deferred. Audio rendered as images is this audio experiment, not the separate video study.

Do not reload the entire historical conversation or all source files. Start with this document, inspect only the nearby code and data needed for the next falsifiable check, then implement and validate incrementally. Record newly measured facts in the repository so the following session does not depend on chat memory.

## Working Rules And Completion

Use Italian in conversation and English in repository documents/application text. No manual wrapping of prose paragraphs. Time every terminal command, report elapsed time, and use single-line PowerShell invocations. Do not ask the user to write code or copy files manually; do ask for unavailable physical recordings, verified diagnoses, credentials entered through a secure path, or material scope/authorization decisions. Never print secrets or persist private spending allowances. Preserve unrelated dirty files and all historical reports; no branch, bulk commit or push without authorization.

The next session is done when the renderer passes meaningful signal/manifest/leakage checks, the real multimodal path has been exercised on the registered bounded experiment, the numerical control and independent evaluator produce an auditable result, and all attempts plus a gate verdict are recorded. If suitable independent data, model access or required decisions are missing, deliver the tested offline tool and a precise blocker; do not call mocks, a synthetic probe, same-recording windows or an untested plan a feasibility result.
