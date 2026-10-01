# Current State

**Develop from the simple reference comparison; do not promote the archived adaptive-memory or pruning variants, or treat consumed inputs as clean evaluation data.** The [method](METHOD.md) defines the central approach, [Results](RESULTS.md) own findings and the [public examples](../examples/README.md) own the inspection snapshot. This document is the maintainer handoff: development gates, data boundaries, runtime constraints and verification.

The next useful step is a better reference set, not a new model policy. Ottawa needs references for each operating profile and load; Jin magnet fracture needs a reference that represents its other microphone regime, chosen without test outcomes. Measure every change against the forced nearest-distance control so the model's own contribution becomes visible. A confirmatory claim requires fresh acquisitions; every current recording has been consumed.

The [Ottawa class-memory pilot](DSP_MEMORY_PROTOCOL.md) completed both 72-acquisition streams and its [measured results](DSP_MEMORY_RESULTS.md) reject the adaptive policy: coverage improves mainly through additional incorrect assignments. Preserve its 32 reserved acquisitions, which remain unmaterialized and locked. The [pruning results](DSP_PRUNING_RESULTS.md) remain a separate negative safety finding. Actual human assessment, private cloud training and operational promotion remain unimplemented. [Benchmark status](DSP_BENCHMARK_STATUS.md) owns the distinction between measured findings, external state of the art and unmeasured human performance.

## Evidence

Use the [documentation map](README.md) to find each study's owning report. Historical protocols and failures remain in [the experiment archive](EXPERIMENTS.md); dataset rights and grouping remain in [Audio Datasets](AUDIO_DATASETS.md). Preserve every frozen local registration and raw artifact; [registered code](../registered/simple-method/README.md) preserves the recovered recorded runner and validator versions. Published examples are consumed, truth-visible review material, not independent human or final evaluation data.

## Keep Reference Expansion Separate From Pruning

The [offline protocol](DSP_OFFLINE_PROTOCOL.md) owns physical-resolution representations and multi-reference aggregation. The class-memory pilot tests reference enrichment as a separate factor with a fixed four-view input in both arms; it does not establish a pruning effect or silently promote the old candidate. Gain compensation does not establish robustness to microphone response, position, reverberation or operating regime.

Represent a class with multiple complementary examples and retain distinct acoustic regimes as separate references rather than averages. The comparative report should expose per-reference and per-class evidence, within-class variability, competing-class margins and disagreements between diagnostics. Every added representation needs an isolated development comparison against the existing baseline and against a numerical-only decision rule.

The intended operational behavior is uncertainty triggering human investigation. The completed memory pilot used publisher labels as a disclosed human oracle, revealing a stream sample's label only after recording an unresolved retrieval-stage review. The observed failure is that wrong known-class assignments bypass this review loop. New-class creation was not tested.

The [dataset guide](AUDIO_DATASETS.md) owns inventories and grouping. The [class-memory protocol](DSP_MEMORY_PROTOCOL.md) owns the allocation, oracle budget and leakage guards. Whole acquisitions cannot cross roles; Jin window subdivision is excluded as a way to manufacture independent cases. Completed development inference does not authorize treating previously exposed data as a clean benchmark.

For a fresh working session, start with this file, the [method](METHOD.md), [Results](RESULTS.md), the [DSP pipeline](DSP_PIPELINE.md) and the [labeled results record](DSP_LABELED_RESULTS.md). Any later inference campaign requires a new bounded registration and explicit separation of reference, calibration and evaluation data. Existing request limits are exhausted or belong to completed experiments.

## Data Boundaries

| Consumer | Allowed inputs | Excluded inputs |
| --- | --- | --- |
| Source audit | Publisher files, labels, license and acquisition metadata | Unreviewed disclosure; only the explicit consumed-example release is public |
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

The publication check scans the staged Git index. Only the curated consumed audio, selected input text/decisions and comparisons under `examples/` are released; complete archives, unselected raw requests, credentials and CLI caches remain excluded. [Publication policy](PUBLICATION.md) owns this boundary. Documentation and application text use English, with one source line per prose paragraph.
