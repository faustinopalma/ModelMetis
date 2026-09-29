# Current State

**No tested configuration supports reliable operational fault diagnosis.** Command-line experiments cover teacher labeling, specialist training, frozen encoders, numerical controls and DSP-to-image comparison. The local review application is separate from those pipelines. Autonomous coordination, adaptive routing and private cloud training remain unimplemented.

## Evidence

| Experiment | Result | Limit |
| --- | --- | --- |
| Teacher-generated labels, EXP-001 to EXP-007 | Poor teacher accuracy and no useful specialist improvement | Public motor/engine sources; no heavy-vehicle validation |
| Jin one-shot encoders, EXP-008 | FISHER, ECHO, EAT and spectral control each 12/12 | Four query recordings; acquisition and encoding confounds |
| Cross-drone transfer, EXP-009 | Forced classification 4-9/54; each geometric policy abstained on 54/54 | One query drone; sparse-reference reliability not established |
| Larger encoders, EXP-010 | Dasheng P@5 27.41%; within-cluster condition agreement 90/751 pairs | Better retrieval, impure clusters |
| STFT-only comparison, EXP-011 | Welch control abstained on 12/12; visual inference not executed | Model deployment unavailable for that run |
| DSP-to-Sol, EXP-012 | 0/9 known trials recognized; 9/9 falsely rejected; 3/3 unknown trials correctly rejected | Three repeated query clips; zero technical failures |

Protocols, failed attempts and measurements belong in [Experiment History](EXPERIMENTS.md), [STFT Results](VISUAL_AUDIO_RESULTS.md) and [DSP-to-Sol Results](DSP_LLM_RESULTS.md). Dataset rights, grouping and confounds belong in [Audio Datasets](AUDIO_DATASETS.md). Existing data, registrations and artifacts remain immutable. Drone C was source-audited but has no model evaluation; B is consumed development data.

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

The deterministic [DSP pipeline](DSP_PIPELINE.md) generates measurements and multiview reports without model calls. [EXP-012](DSP_LLM_PROTOCOL.md) uses exact FFT/STFT images and typed measurements. It completed against pinned Sol on the reused resource; its negative classification result is recorded separately from infrastructure success.

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
