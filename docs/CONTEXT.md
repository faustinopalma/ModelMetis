# Current State

**Shape-based comparison on Jin is promising, while joint recognition and exception handling remain unresolved.** Reports plus numerical distances achieved 11/12 correct known labels and 2/4 correct excluded-class rejections. A calibrated replay achieved 9/12 and 4/4 respectively; Ottawa achieved 4/16 known labels. The next step is to improve deterministic DSP comparison before running further model experiments. Autonomous human-loop enrichment, adaptive routing and private cloud training remain unimplemented.

## Evidence

| Experiment | Result | Limit |
| --- | --- | --- |
| Teacher-generated labels, EXP-001 to EXP-007 | Poor teacher accuracy and no useful specialist improvement | Public motor/engine sources; no heavy-vehicle validation |
| Jin one-shot encoders, EXP-008 | FISHER, ECHO, EAT and spectral control each 12/12 | Four query recordings; acquisition and encoding confounds |
| Cross-drone transfer, EXP-009 | Forced classification 4-9/54; each geometric policy abstained on 54/54 | One query drone; sparse-reference reliability not established |
| Larger encoders, EXP-010 | Dasheng P@5 27.41%; within-cluster condition agreement 90/751 pairs | Better retrieval, impure clusters |
| STFT-only comparison, EXP-011 | Welch control abstained on 12/12; visual inference not executed | Model deployment unavailable for that run |
| DSP-to-Sol, EXP-012 | 0/9 known trials recognized; 9/9 falsely rejected; 3/3 unknown trials correctly rejected | Three repeated query clips; zero technical failures |
| Labeled DSP comparison, Jin | Development improved from 5/8 to 8/8 with numerical evidence; reserved-direction recognition 11/12, excluded-class rejection 2/4 | Twelve query windows share four previously consumed acquisitions; numerical control already achieved 8/8 on development |
| Class-calibrated Jin replay | Known recognition 9/12, excluded-class rejection 4/4 | Eight additional labeled calibration windows; all three magnet-fracture queries falsely rejected; exploratory replay |
| Labeled DSP comparison, Ottawa | Known recognition 4/16, twelve wrong-class assignments | One reference per class across operating-profile changes |

Protocols, failed attempts and measurements belong in [Experiment History](EXPERIMENTS.md), [STFT Results](VISUAL_AUDIO_RESULTS.md), [DSP-to-Sol Results](DSP_LLM_RESULTS.md) and [Labeled DSP Results](DSP_LABELED_RESULTS.md). The labeled run retained 68 HTTP attempts: 64 completed classifications, one paid truncation and three service rejections with missing usage. Known list-price consumption was USD 8.43773744. Dataset rights, grouping and confounds belong in [Audio Datasets](AUDIO_DATASETS.md). Existing data, registrations and artifacts remain immutable. Drone C was source-audited but has no model evaluation; B is consumed development data.

The local labeled-results index is `outputs/dsp-labeled-results-v1/index.html`. The [human comparison page](HUMAN_AUDIO_COMPARISON.md), `outputs/audio-comparison-v8/index.html`, exposes correct publisher labels, selects the matching reference, supports keyboard reference switching and A/B listening, and highlights wrong-class assignments and false rejections separately from technical failures. It contains 36 query windows and 12 references; these are a selected subset of the available data. Label-free human testing is outside the current review-page workflow.

## Strengthen DSP Before Adaptive Experiments

The next work should implement and validate a comparative DSP report, following the [prioritized DSP extensions](DSP_PIPELINE.md#prioritize-shape-comparison-extensions). Preserve the existing measured results as baselines. The current comparison compensates uniform gain by mean-centering log spectra; its dB thresholds measure spectral-shape distance. Microphone response, position, reverberation and operating regime can still alter the shape. Diagnostic similarity should emphasize stable structural evidence while recording amplitude as acquisition-quality context.

Represent a class with multiple complementary examples and retain distinct acoustic regimes. The comparative report should expose per-reference and per-class evidence, within-class variability, competing-class margins and disagreements between diagnostics. Every added representation needs an isolated development comparison against the existing baseline and against a numerical-only decision rule, so the contribution of model interpretation is measurable.

The intended operational behavior is `different` triggering human investigation. A reviewer may assign the exception to an existing class or establish a new class; the confirmed example then enriches a versioned reference bank. The proposed simulation uses publisher labels as a disclosed human oracle, revealing a stream sample's label only after recording the model's rejection. Score the original decision before enrichment, and measure improvement on subsequent inputs. Track accepted-label errors, automatic coverage, human interventions and reference-bank growth together. Samples assigned to a wrong known class will not trigger this rejection-only loop, so their errors must remain visible in evaluation.

There are 346 prepared WAVs across Ottawa (128), Jin (136), AI Mechanic (19) and the A/B drone package (63). The local Jin sources comprise 12 original recordings and permit 721 nonoverlapping ten-second windows. The A/B archives contain 215,974 labeled half-second clips before dependency-aware selection; paired microphones and noise variants require grouping. A proposed Ottawa pilot uses eight seed references, 104 sequential acquisitions and 16 separate evaluation acquisitions. This allocation is a proposal, and the data already have project exposure. No enrichment experiment has been executed or authorized by the completed registrations.

For a fresh working session, start with this file, [DSP Pipeline](DSP_PIPELINE.md), [Labeled DSP Results](DSP_LABELED_RESULTS.md) and [Human Audio Comparison](HUMAN_AUDIO_COMPARISON.md). Establish the DSP design and offline validation first. Any later inference campaign requires a new bounded registration and explicit separation of reference, enrichment-stream and evaluation data. Existing request limits are exhausted or belong to completed experiments.

## Data Boundaries

| Consumer | Allowed inputs | Excluded inputs |
| --- | --- | --- |
| Source audit | Publisher files, labels, license and acquisition metadata | Publication of private mappings or sample-level answers |
| Teacher or frozen encoder | Sanitized audio, taxonomy, fixed context and disjoint support examples | Query labels, source filenames, fault-coded IDs and evaluator output |
| Operational specialist | Training audio, teacher silver labels, explicit human corrections and provenance | Publisher targets, held-out samples and source mappings |
| Supervised diagnostic control | Separate training labels or disclosed support package | Query labels during fitting; operational promotion authority |
| Coordinator | Training evidence, bounded development metrics, costs and lineage | Final gold labels, per-example gold errors and evaluator credentials |
| Blind reviewer | Sanitized sample, taxonomy and allowed context | Publisher labels; model predictions during independent review |
| Sealed evaluator | Frozen predictions and hidden references | Relabeling training data or modifying candidates |

Split physical units and original acquisitions before segmentation. Keep duplicates, channels, microphone pairs and augmentations together. Operational IDs are opaque; strip answer-bearing metadata and keep reversible source mappings in restricted storage. Local files and allowlisted interfaces prevent accidental leakage but do not enforce OS-level isolation.

Teacher predictions remain silver. Confirmed human diagnoses are gold; publisher-derived support labels use `simulated_human_from_publisher`. Support and query audio/groups must be disjoint. Evaluation predictions never enter training. Consumed evaluation data cannot become fresh confirmation data, and benchmark masking does not rule out pretraining exposure.

## Experiment Constraints

- Use very few initial labeled references and occasional confirmed additions. Measure accepted-label error, automatic coverage and total human effort together; routine annotation expansion is outside the current design.
- Distance and model confidence are uncalibrated unless independently validated. Abstain on ambiguous, novel or unusable input. Keep outside-reference outcomes distinct from fault diagnoses.
- Freeze hypotheses, source selection, rendering, prompts, models, budgets, thresholds and stopping rules before evaluation. Record failures and retries; preserve hash-bound runners and preparations.
- Human reference updates require versioning and validation. Automatic labels cannot redefine gold references or silently expand the taxonomy.
- Candidate proposals may use an LLM. Permissions, budgets, promotion and rollback use deterministic gates. Training completion or teacher/student agreement does not satisfy an accuracy gate.
- New experiments require a separate protocol. No additional silver collection, reference expansion, specialist training or promotion follows automatically from the negative results.

See the [sparse-annotation contract](ADAPTIVE_MODELS.md#sparse-human-annotation-contract), [audio objectives](AUDIO_OBJECTIVES.md), [validation protocol](VALIDAZIONE.md) and [backlog](BACKLOG.md). Video feasibility remains deferred.

## Implementation And Infrastructure

The local FastAPI API and React console support sanitized WAV upload/playback and versioned review. Their labels (`healthy`, `fault_unspecified`, `needs_review`) are independent of experiment taxonomies. Model inference is not integrated into the review API. Authentication and cloud persistence are missing; retain the loopback guard and production-mode refusal.

The native Windows ARM64 application runtime is `.venv/Scripts/python.exe`; ML uses the separate x64 runtime under `data/ml-runtime`. Reproduction and dependency snapshots are in the [ML guide](../ml/README.md) and [scripts guide](../scripts/README.md). Do not merge runtimes or overwrite frozen data to reproduce a run.

The deterministic [DSP pipeline](DSP_PIPELINE.md) generates measurements and multiview reports without model calls. [EXP-012](DSP_LLM_PROTOCOL.md) uses exact FFT/STFT images and typed measurements. The later [whole-report comparison](DSP_REPORT_COMPARISON.md) includes all generated figures, declared compact image derivatives, typed measurements and optional numerical distances. Labeled experiment results are separate from transport success. The offline human-review generator uses the same source WAVs and original report figures, with source and artifact hash checks.

Infrastructure state and target identifiers are maintained in [infra](../infra/README.md), [DSP resource reuse](DSP_RESOURCE_REUSE.md) and [AML infrastructure](AML_INFRASTRUCTURE.md). The Global Standard quota request was submitted; approval remains unverified. Its status is independent of the completed DataZoneStandard experiment. Check live state before further operations; never replay a pending deployment or duplicate a quota request.

New resources use IaC and dedicated ModelMetis groups; the documented DSP reuse is a specific exception. Preserve unrelated resources and deployment state. Storage requires disabled public access, private endpoints, private DNS and managed-identity access from an authenticated VNet-connected workload. Public CI runners and browsers cannot directly reach private storage. AML compute, private-data access and GPU shutdown remain unverified.

## Verification

Check the worktree before editing and preserve parallel changes. Use the [test guide](../tests/README.md) for coverage and limitations. Run focused checks for changed behavior; historical test counts are not evidence for the current tree.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe -m scripts.check_publication
```

The publication check scans the staged Git index. Raw data, per-example answers, credentials, CLI caches, request bodies and contact receipts stay out of Git. Documentation and application text use English, with one line per prose paragraph.
