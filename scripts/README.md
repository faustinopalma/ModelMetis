# Automation

The local audio experiment separates reference-aware import/evaluation from teacher and training worker inputs. None of these Python scripts provisions cloud infrastructure.

| Command | Allowed input | Output |
| --- | --- | --- |
| `prepare_ottawa.py` | Publisher ZIP, including source names and labels | New canonical WAV partitions, opaque manifests, separate sealed references and aggregate audit |
| `prepare_mechanic.py` | Versioned AI Mechanic ZIP and source annotations | Constant-signal exclusions, duplicate checks, one canonical window per source and masked development/train partitions |
| `prepare_mechanic.py --support-from` | Frozen masked source plus sealed references, explicit taxonomy | One simulated-human support example per class from training only; disjoint remaining train and unchanged development |
| `prepare_jin.py` | Original Jin v1 PCB WAVs plus verified official catalog | Direction-grouped 4 support/120 train/12 development windows, canonical WAVs and isolated source/training references |
| `audit_drone.py` | Three pinned drone v1 TAR archives, including publisher names/labels | Immutable restricted SQLite inventory and aggregate JSON; no TAR extraction, operational partition or model execution |
| `python -m scripts.prepare_drone` | Completed audited inventory and verified A/B source TARs | Nine masked A supports, 54 B queries, separate sealed references and retained preparation evidence |
| `python -m scripts.drone_experiment campaign` | Local pinned checkpoints; synthetic input or masked drone inputs plus explicit support | Bounded probe/inference workers, frozen geometry, separate forced/selective reports and fixed mixture |
| `python -m scripts.evaluate_drone` | Complete campaign, masked dataset, sealed B references and retained probe attempts | Hash-checked aggregate metrics, selective coverage/error and annotation accounting; no per-query answers |
| `supervised_control.py train` | Dedicated publisher training references or explicit one-shot support, fixed method | Clearly marked diagnostic control, not operational silver or a promoted specialist |
| `supervised_control.py predict` | Held-out unlabeled partition and trusted local control artifact | Predictions after training audio/group overlap rejection; no query references |
| `encoder_experiment.py campaign` | Masked Jin development audio and explicit one-shot support | Bounded frozen-encoder workers, hashes, timings, preserved failures and uniform mixture; no query references |
| `encoder_experiment.py mixture` | Completed aligned distinct-encoder predictions | New immutable uniform mixture with member hashes and full inference costs |
| `encoder_experiment.py report` | Evaluated predictions, model files, campaign and explicit execution notes | Hash-verified aggregate evidence without query-level outputs |
| `python -m modelmetis.simulation infer` | One operational partition and a fixed prompt candidate | Teacher predictions with prompt/audio hashes, failures and timing |
| `python -m modelmetis.simulation infer-audio` | Development/train partition, frozen prompt, endpoint, ledger and optional authorized support package | Bounded audio requests, conservative accounting, prompt/support provenance and safe progress |
| `python -m modelmetis.simulation train` | Train partition and completed teacher silver collection | Specialist artifact and training provenance; no publisher reference input |
| `python -m modelmetis.simulation predict` | Held-out operational partition and trusted local model | Frozen specialist predictions |
| `evaluate_audio.py` | Completed predictions and sealed references for development or test | Aggregate metrics; development-only prompt selection; no training labels |
| `learning_curve.py` | Frozen training silver, train/development paths, sealed reference path for evaluator subprocess only | Checkpointed arrival snapshots, expected one-class blocks and separate aggregate evaluation |
| `report_audio.py` | Local campaign roots and usage ledgers | Reconciled versionable aggregate evidence, without sample-level answers or provider text |

All commands run from the repository root with the ML dependencies and `PYTHONPATH=src`. Import requires a new output directory; it will not overwrite an existing split. Preserve the downloaded archive outside Git. The measured source and model results, runtime snapshot and complete worker commands are in the [ML experiment guide](../ml/README.md).

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; data/ml-runtime/Scripts/python.exe scripts/prepare_ottawa.py --archive data/ottawa-v2.zip --output data/ottawa-reimport; if ($LASTEXITCODE) { throw 'Source audit/import failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The importer generates new UUIDs when writing a new split. This preserves grouping but not the original sample IDs or stream order. A replay of the recorded run must retain its original manifests. CSV/MAT format copies are checked and treated as one acquisition; windows and augmented data are not created by this importer.

Pending automation: process-enforced deadlines, resumable immutable collections, authenticated snapshot publication, ML job submission/termination verification, invoice reconciliation, strategy coordination and rollback testing. CLAP inference has no request limit or wall-clock timeout. The audio LLM path enforces a persistent request limit and records conservative consumption, plus a scheduling deadline but not a hard process deadline. Neither worker resumes into an existing output directory. Dedicated audio infrastructure was deployed through local Bicep templates; these locally modified templates are not included in this experimental-results publication. Inference requires a separately authorized compatible endpoint and identity; the recorded endpoint is not a public demonstration service.

## Embedding Similarity And Larger Encoders

[EXP-010](../docs/EXPERIMENTS.md#exp-010-similarity-geometry-and-larger-encoders) tests similarity without diagnostic naming. [The fixed protocol](../docs/EMBEDDING_SIMILARITY.md) defines the registered model revisions, cosine retrieval, HDBSCAN settings and limits. `scripts.larger_encoders` downloads, probes and extracts EAT-large20/Dasheng vectors using the existing x64 runtime. `scripts.embedding_geometry` computes all label-blind decisions before reading sealed B references, independently checks distances/rank-sum AUC, and publishes aggregate-only evidence. No model fitting, C access, cluster tuning or automatic gold propagation.

The current local artifacts already contain the downloads, eight successful larger-model attempts and all five encoder vectors. To reproduce evaluation without new inference, use a new output location:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { .venv/Scripts/python.exe -m scripts.embedding_geometry --runs artifacts/drone-one-shot-v1/fisher artifacts/drone-one-shot-v1/echo artifacts/drone-one-shot-v1/eat artifacts/larger-extract-v1/eat_large artifacts/larger-extract-v1/dasheng_12b --output artifacts/geometry-reproduction --campaigns artifacts/larger-metadata-v1 artifacts/larger-download-v1 artifacts/larger-probe-v1 artifacts/larger-extract-v1 --publish artifacts/geometry-reproduction-aggregate.json; if ($LASTEXITCODE) { throw 'Geometry verification failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

A complete model replay uses the same masked dataset and reviewed pinned model sources, but separate immutable attempt folders. Metadata/source inspection must precede executing newly downloaded custom code; all four EAT source files matched the previously reviewed base version. The existing encoder runtime pins (`ml/requirements-encoder-windows-x64.txt`; local-only) suffice; no package upgrade was needed. Each child process has a 600-second deadline, and detailed progress is in its log. Campaign JSON, not merely the parent process exit code, records individual failures or timeouts; the evaluator refuses incomplete model attempts.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.larger_encoders campaign --phase metadata --output artifacts/larger-metadata-reproduction } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.larger_encoders campaign --phase download --output artifacts/larger-download-reproduction } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.larger_encoders campaign --phase probe --downloads artifacts/larger-download-reproduction --output artifacts/larger-probe-reproduction } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.larger_encoders campaign --phase extract --downloads artifacts/larger-download-reproduction --output artifacts/larger-extract-reproduction } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Replace the larger-model run/campaign locations in the evaluation command to evaluate a new extraction. Repeating the same consumed clips is a technical replay, not new scientific evidence. Query labels and original paths never enter encoder inputs; support labels are validated for package compatibility but not used for fitting or similarity. Source labels remain available to the separate evaluator/curator. The frozen protocol and artifact hashes remain essential; these local boundaries are not an OS sandbox.

## Drone Source Audit

Install the `audit` extra in the native application environment. The decoder recognizes WAV and FLAC content independently of `.wav` filenames, verifies format/sample count, and compares canonical decoded PCM. FFmpeg is used only after a libsndfile FLAC read failure; every FLAC decode must match its embedded PCM MD5. Archive size and publisher MD5 are mandatory; SHA-256 and decoder versions are recorded. Label-free filenames stay null, never guessed. Original paths, condition codes and PCM mappings in `restricted.sqlite` are source-audit information, not model inputs or public artifacts. Filesystem separation prevents accidental leakage, not arbitrary access by code running under the same user.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { .venv/Scripts/python.exe -m pip install -e ".[audit]"; if ($LASTEXITCODE) { throw 'Audit dependency installation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { .venv/Scripts/python.exe scripts/audit_drone.py --source data/drone-source-v1 --output artifacts/drone-audit-replay; if ($LASTEXITCODE) { throw 'Inspect retained drone audit failure' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Use a new output directory; preserve successful and failed attempts. The command checks all 324,000 files without selecting supports or repairing annotations. Reuse existing source archives. [Audit results](../docs/AUDIO_DATASETS.md#drone-archive-audit) and the aggregate (`ml/drone-v1-audit.json`; local-only) retain all five attempts. Filename groups, channels and segments do not count independent drones. Preparation and inference are separate commands below.

## Cross-Drone One-Shot Experiment

[EXP-009](../docs/EXPERIMENTS.md#exp-009-cross-drone-one-shot-and-abstention) completed with negative results. The importer runs in the native environment with `audit` dependencies; the model campaign uses the existing x64 encoder runtime and local cache. Exactly nine A support labels and 54 B queries are permitted. Both support and query manifests identify entire physical drones, with explicitly allowed shared support grouping but no cross-role audio/group overlap. C is not a supported worker partition. This is a code-level input contract, not an OS sandbox or protection against deliberately supplying a different disguised dataset.

Historical input preparation used `python -m scripts.prepare_drone --source data/drone-source-v1 --inventory artifacts/drone-audit-v5 --output data/drone-one-shot-v1`. Keep that frozen output for replay; regenerating produces new UUIDs, not independent statistical evidence. Two successful synthetic campaigns are retained as `artifacts/drone-probe-v1` and `artifacts/drone-probe-v2`. The second matches the final runner. For a new technical replay, use new output directories and the retained preregistration snapshot so subsequent results text does not change the protocol hash:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.drone_experiment campaign --phase probe --protocol artifacts/drone-one-shot-v1/registered-protocol.md --output artifacts/drone-probe-replay; if ($LASTEXITCODE) { throw 'Probe campaign failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { data/ml-runtime/Scripts/python.exe -m scripts.drone_experiment campaign --phase worker --input data/drone-one-shot-v1/development --support data/drone-one-shot-v1/support --probes artifacts/drone-probe-replay --protocol artifacts/drone-one-shot-v1/registered-protocol.md --output artifacts/drone-one-shot-replay; if ($LASTEXITCODE) { throw 'Inspect retained campaign attempts' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Every candidate has a 600-second process deadline and an immutable log. Campaign completion means scheduling finished, not that every candidate passed; inspect each status. The worker requires a successful synthetic probe with matching runner, encoder, classifier, loader and protocol hashes before opening real inputs. Checkpoint source/weights must match EXP-008 registration. No network download, source reference lookup, additional support label, threshold fitting or n-shot mode occurs. Query embeddings remain ignored artifacts for arithmetic checks, not an adaptive training set. The mixture averages complete aligned encoder outputs and has no geometric rejection rule.

The isolated evaluator reproduces the existing aggregate without model calls; it checks input/reference hashes, campaign/log/worker integrity, prediction hashes, mixture membership and sample coverage before reporting. Use a new output path:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { .venv/Scripts/python.exe -m scripts.evaluate_drone --dataset data/drone-one-shot-v1 --campaign artifacts/drone-one-shot-v1 --probes artifacts/drone-probe-v1 artifacts/drone-probe-v2 --output artifacts/drone-evaluation-replay.json; if ($LASTEXITCODE) { throw 'Drone evidence reconciliation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The aggregate (`ml/drone-one-shot-v1.json`; local-only) records nine model-visible support labels, 54 evaluator answers, full publisher-inventory use for source curation and zero added gold reviews. All three geometric policies had zero accepted cases; their accepted error is null, not zero. The review queue, reference versioning/updates, unknown-fault validation and reliable operational routing remain unimplemented.

## Generative Audio Experiment

The newer non-generative track is documented under [Frozen Encoder Experiment](#frozen-encoder-experiment); the following sections retain the original teacher experiments.

EXP-002 through EXP-005 use a deployed, authorized dedicated endpoint with a passed two-input real synthetic capability check. The [experiment history](../docs/EXPERIMENTS.md) records technical failures, frozen prompts, model/version, price assumptions, completed development comparisons and executed or blocked snapshots. The endpoint is `https://aoai-modelmetis-dev-iydoch6uxaxx6.openai.azure.com/`; set `MODELMETIS_AUDIO_ENDPOINT` to that dedicated resource, never an existing project. Do not record private spending ceilings in files or command arguments. All registered comparisons are finished; the following historical command is not an instruction to spend on an unregistered replay, and its output path already exists.

Use the ignored x64 `data/ml-runtime` environment: [audio runtime pins](../ml/requirements-audio-windows-x64.txt) include the original ML pins plus Azure Identity and HTTP dependencies. On September 18 the native ARM64 environment could not install the required cryptography wheel; do not switch the application interpreter. The worker verifies subscription and tenant separately, then uses a subscription-only `AzureCliCredential`, without keys, interactive fallback or token logging. Passing both tenant and subscription to the actual CLI token request failed despite successful credential construction. For local execution, use the personal Azure CLI profile: the workspace `.azure` belongs to unrelated prior state and is not the authorized target profile.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; $env:AZURE_CONFIG_DIR=Join-Path $HOME '.azure'; data/ml-runtime/Scripts/python.exe -m modelmetis.simulation infer-audio --input data/ottawa-simulation-v1/development --prompts configs/audio-llm-prompts.json --variant direct-v1 --endpoint $env:MODELMETIS_AUDIO_ENDPOINT --deployment modelmetis-audio-teacher --tenant-id 39d764bc-ae80-46f9-b22c-6246cc5a20c2 --subscription 7ecf802f-04ac-4e81-8703-c3d39074f823 --resource-group rg-modelmetis-dev-audio-swc --ledger artifacts/ottawa-v2/usage.json --max-requests 160 --output artifacts/ottawa-v2/dev-direct --acknowledge-paid-requests; if ($LASTEXITCODE) { throw 'Audio attempt failed; inspect its report' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The evidence prompt uses `--variant evidence-v1` and a different new output directory, but the same ledger. Collection uses only the `train` directory with the development-selected frozen variant. Never create a fresh ledger merely to bypass a request limit. The conservative reservation is USD 4.11 per in-flight request; returned valid usage reduces it, unknown usage retains it. Stop conditions include the request limit, insufficient scheduling headroom and the first failed teacher request. A 429 is recorded as a failure rather than retried invisibly. Generated confidence is uncalibrated; an explicit null remains an abstention at threshold zero.

Each report records the entire prompt hash, individual audio hashes, source and manifest hashes, UTC interval, safe status, model/API settings and estimated cost. Reports are local and ignored by Git. A changed prompt requires a new attempt/output, not overwriting an existing collection. Azure returns `gpt-audio-1.5` without a date; the worker accepts it only after checking deployed version `2026-02-23`, successful state and `NoAutoUpgrade` through ARM. The final `test` partition is deliberately rejected by `infer-audio` because its previous evaluation has been consumed.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; data/ml-runtime/Scripts/python.exe scripts/learning_curve.py --input data/mechanic-simulation-v1/train --silver artifacts/mechanic-v1/train-silver/predictions.json --development data/mechanic-simulation-v1/development --references data/mechanic-simulation-v1/sealed/references.json --sizes 4 8 11 --output artifacts/mechanic-v1/learning-curve-replay; if ($LASTEXITCODE) { throw 'Learning curve failed; inspect its checkpoint' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Ottawa's proposed 16/32/64/96 snapshots were blocked because the selected teachers collapsed to one class. The real AI Mechanic 4/8/11 curve used the frozen manifests above: four arrivals blocked; eight and eleven fitted, with negative independent development results. A replay needs a new output directory and does not create fresh statistical evidence. Counts refer to observed arrivals, including abstentions, in a deterministic shuffled opaque-ID order; fitting uses accepted silver from that prefix. There is no truth-based stratification or class filling. The entire silver collection is validated before any subset fit. The curve runner treats only the known no-label/one-class exceptions as expected blocks; other failures stop with a checkpoint. It gives each local worker a 120-second process timeout. These are bounded commands, not an autonomous strategy-selection or promotion loop, and subprocess inputs are not an OS-enforced filesystem sandbox.

The aggregate report can be reproduced without LLM calls or source-reference input:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; data/ml-runtime/Scripts/python.exe scripts/report_audio.py --roots artifacts/ottawa-v2 artifacts/ottawa-v3 artifacts/mechanic-v1 --output artifacts/audio-evidence-replay.json; if ($LASTEXITCODE) { throw 'Evidence reconciliation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The report generator fails on empty attempts, duplicate roots or ledger mismatches. It reconciled 109 reservations, 108 HTTP responses with known usage and all 14 attempts on September 18. [The preserved report](../ml/audio-experiments-20260918.json) includes aggregate development metrics and learning curves; local originals retain detailed hashes. Prompt v1 files remain immutable. Later explicit options select audio-derived measurements, system-message instructions or DC/peak normalization, with separate frozen configurations and transmitted-audio hashes when normalized. No parser repair or hidden retry is enabled.

## One-Shot Experiment

EXP-006 discloses four support labels with `simulated_human_from_publisher` provenance. Lowest canonical-audio SHA256 per class selects supports from training, leaving seven unlabeled samples and eight unchanged development inputs. Export includes opaque IDs/groups, labels and audio hashes. The loader enforces one example per class and rejects query ID/group/audio overlap before accounting or networking. No n-shot mode is implemented.

Historical commands below produced the preserved outputs and cannot be rerun over them. Repeating a paid experiment requires a separately registered attempt; do not replace the exhausted ledger or select different support samples to bypass the cap.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; data/ml-runtime/Scripts/python.exe scripts/prepare_mechanic.py --support-from data/mechanic-simulation-v1 --prompts configs/mechanic-audio-prompts-v4.json --variant mechanic-one-shot-v1 --output data/mechanic-one-shot-v1; if ($LASTEXITCODE) { throw 'Support export failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; $env:AZURE_CONFIG_DIR=Join-Path $HOME '.azure'; data/ml-runtime/Scripts/python.exe -m modelmetis.simulation infer-audio --input data/mechanic-one-shot-v1/development --support data/mechanic-one-shot-v1/support --prompts configs/mechanic-audio-prompts-v4.json --variant mechanic-one-shot-v1 --endpoint https://aoai-modelmetis-dev-iydoch6uxaxx6.openai.azure.com/ --deployment modelmetis-audio-teacher --tenant-id 39d764bc-ae80-46f9-b22c-6246cc5a20c2 --subscription 7ecf802f-04ac-4e81-8703-c3d39074f823 --resource-group rg-modelmetis-dev-audio-swc --ledger artifacts/mechanic-one-shot-v1/usage.json --max-requests 8 --deadline-seconds 900 --minimum-score 0 --acknowledge-paid-requests --output artifacts/mechanic-one-shot-v1/dev-one-shot; if ($LASTEXITCODE) { throw 'Inspect preserved one-shot checkpoint' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The base prompt equals direct-v2; the worker binds the ordered support digest into its effective prompt, adds the four audio/label pairs and records their manifest hash/provenance. Neither support IDs nor hashes reach the model. Each HTTP call includes all four reference recordings plus the query; token accounting includes them. The first real request verified this multi-audio layout without an extra capability call. Eight calls succeeded, but accuracy stayed 3/8 and macro-F1 fell slightly. The [full protocol/results](../docs/EXPERIMENTS.md#exp-006-one-audio-example-per-category) retain all details. No collection or training followed.

To reproduce the updated aggregate evidence without network calls, use a new output path:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; data/ml-runtime/Scripts/python.exe scripts/report_audio.py --roots artifacts/ottawa-v2 artifacts/ottawa-v3 artifacts/mechanic-v1 artifacts/mechanic-one-shot-v1 --output artifacts/audio-one-shot-evidence-replay.json; if ($LASTEXITCODE) { throw 'Evidence reconciliation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The [new aggregate report](../ml/audio-experiments-20260918-one-shot.json) preserves all 15 attempts and five development comparisons; the old aggregate remains intact. Support provenance is allowlisted; sample mappings and answers are excluded. Every command must report its duration, return nonzero on failure, verify nonempty work when expected and avoid duplicating effects. Use parameters and input files instead of credentials or complex payloads on the command line.

## Jin Direction-Transfer Controls

EXP-007 follows a supervised audio-only literature review, then compares the real generative teacher with explicitly isolated publisher-supervised diagnostic controls. The [protocol/results](../docs/EXPERIMENTS.md#exp-007-new-motor-data-with-supervised-diagnostic-controls) and [aggregate comparison](../ml/jin-directions-v1.json) record the actual outcomes. The operational `simulation train` entrypoint still accepts teacher silver only. Never submit a control artifact to that workflow or present publisher labels as silver.

Source preparation requires `data/raw/jin-v1/catalog.json`, twelve original PCB WAVs and their legend. The official CC BY 4.0 dataset is [Mendeley 9dpmkgpncw, version 1](https://data.mendeley.com/datasets/9dpmkgpncw/1). Its public catalog endpoint is `https://data.mendeley.com/public-api/datasets/9dpmkgpncw/files?folder_id=83ef5cf2-e5ad-4763-bf8c-f71c971237a0&version=1`, with Accept `application/vnd.mendeley-public-dataset.1+json`. Preserve each selected official file record as an `entry` in the catalog array; the importer verifies the exact filename set and `content_details.sha256_hash` for all twelve WAVs before exporting. The original download also verified the legend checksum. Do not use noise mixes or smartphone copies as independent training/test acquisitions. Preserve frozen UUID manifests; reimporting makes different IDs and does not provide new independent evidence.

The historical commands below have already run. Their output paths now exist and refuse overwrite. A local replay needs a different output prefix; another paid teacher run needs a new preregistered question, not replacement of the exhausted twelve-request ledger.

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; & data/ml-runtime/Scripts/python.exe scripts/prepare_jin.py --source data/raw/jin-v1 --output data/jin-directions-v1; if ($LASTEXITCODE) { throw 'Jin import failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; foreach ($method in @('welch-logistic','mfcc-svm')) { foreach ($regime in @('one-shot','full')) { $destination="artifacts/jin-directions-v1/controls/$regime-$method"; $origin=if ($regime -eq 'one-shot') { @('--input','data/jin-directions-v1/support','--support-taxonomy','healthy','magnet_fracture','excess_hall_adhesive','tight_bearing') } else { @('--input','data/jin-directions-v1/train','--references','data/jin-directions-v1/sealed/supervised-train.json') }; & data/ml-runtime/Scripts/python.exe scripts/supervised_control.py train @origin --method $method --output $destination; if ($LASTEXITCODE) { throw 'Control fitting failed' }; & data/ml-runtime/Scripts/python.exe scripts/supervised_control.py predict --input data/jin-directions-v1/development --artifact "$destination/control.joblib" --output "$destination/development.json"; if ($LASTEXITCODE) { throw 'Control prediction failed' }; & data/ml-runtime/Scripts/python.exe scripts/evaluate_audio.py --references data/jin-directions-v1/sealed/references.json --predictions "$destination/development.json" --partition development --output "$destination/evaluation.json"; if ($LASTEXITCODE) { throw 'Control evaluation failed' } } } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; $env:AZURE_CONFIG_DIR=Join-Path $HOME '.azure'; & data/ml-runtime/Scripts/python.exe -m modelmetis.simulation infer-audio --input data/jin-directions-v1/development --prompts configs/jin-audio-prompts.json --variant jin-one-shot-v1 --support data/jin-directions-v1/support --endpoint https://aoai-modelmetis-dev-iydoch6uxaxx6.openai.azure.com/ --deployment modelmetis-audio-teacher --tenant-id 39d764bc-ae80-46f9-b22c-6246cc5a20c2 --subscription 7ecf802f-04ac-4e81-8703-c3d39074f823 --resource-group rg-modelmetis-dev-audio-swc --ledger artifacts/jin-directions-v1/usage.json --max-requests 12 --deadline-seconds 600 --acknowledge-paid-requests --output artifacts/jin-directions-v1/one-shot; if ($LASTEXITCODE) { throw 'Inspect retained teacher evidence' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
$timer=[Diagnostics.Stopwatch]::StartNew(); try { & data/ml-runtime/Scripts/python.exe scripts/evaluate_audio.py --references data/jin-directions-v1/sealed/references.json --predictions artifacts/jin-directions-v1/one-shot/predictions.json --partition development --output artifacts/jin-directions-v1/development.json; if ($LASTEXITCODE) { throw 'Teacher evaluation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Control fit inputs must be training-only with exact reference coverage and matching audio hashes. Prediction refuses training audio/group overlap before computing outputs. Fitting and prediction are separate processes; only the evaluator sees development references. This is accidental-leakage prevention, not OS-enforced access control. Load only locally produced, trusted joblib artifacts: deserialization can execute code. MFCC requires librosa from the pinned x64 audio environment; no new package was installed for this experiment. The four fits and predictions took 168.5 seconds together; the teacher command took 117.2 seconds. Lazy imports/JIT affect MFCC timings. The historical control `load_seconds=0` is an unmeasured placeholder; do not use it to claim zero model loading cost.

The current cumulative report is reproducible offline with a new output path:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; & data/ml-runtime/Scripts/python.exe scripts/report_audio.py --roots artifacts/ottawa-v2 artifacts/ottawa-v3 artifacts/mechanic-v1 artifacts/mechanic-one-shot-v1 artifacts/jin-directions-v1 --output artifacts/audio-jin-evidence-replay.json; if ($LASTEXITCODE) { throw 'Evidence reconciliation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The [sixteen-attempt report](../ml/audio-experiments-20260918-jin.json) contains the paid campaigns only. The [Jin comparison](../ml/jin-directions-v1.json) additionally exports each of the four control directories' `training.json` and `evaluation.json` metrics, the aggregate importer audit and the teacher's aggregate metrics/accounting. Export checked control weight hashes against both training and prediction records and checked prediction hashes against evaluation before publishing aggregates. It contains no per-example predictions, IDs or source filenames. The earlier cumulative reports and all local evidence are preserved. No diagnostic control is promoted, and the teacher's failed threshold stopped further silver collection.

## Frozen Encoder Experiment

EXP-008 implements the first stage of the [adaptive-model protocol](../docs/ADAPTIVE_MODELS.md). Use the existing x64 ML runtime and encoder dependency extension (`ml/requirements-encoder-windows-x64.txt`; local-only), not the ARM64 application environment. The script is a registered Jin-specific experiment, not a general autonomous agent. It fixes four classes, one support per class, model revisions, seed 17, four torch threads, CPU float32, cosine centroids and uncalibrated temperature-1 softmax. No Azure SDK or metered endpoint is invoked. Each candidate is a separate process, with a 600-second hard timeout including download; timeout kills that worker. A completed campaign means all candidates have an outcome, not that all succeeded.

Before executing downloaded Python, inspect the pinned model sources and configuration. Keep the reviewed files in `data/encoder-models/{fisher,echo,eat}`; the campaign downloads the matching safetensors, records hashes and loads from local files with offline flags. These flags are not an OS network sandbox. ECHO and EAT load safetensors with strict state matching; FISHER rejects missing/unexpected/mismatched keys through Transformers loading diagnostics. BEATs is explicitly blocked in this registration because its official Iter3 checkpoint returned HTTP 403; rerunning the campaign does not retest that URL or silently use a mirror. A recovered BEATs attempt needs a recorded source-verification change.

The initial historical campaign command was:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; & data/ml-runtime/Scripts/python.exe scripts/encoder_experiment.py campaign --input data/jin-directions-v1/development --support data/jin-directions-v1/support --output artifacts/encoder-jin-v1; if ($LASTEXITCODE) { throw 'Inspect retained encoder campaign' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

That output exists and cannot be overwritten. FISHER and ECHO completed; EAT initially failed on a nested dynamic-module import, then completed with unchanged weights/preprocessing after direct local-package loading was implemented. Its recovery used the `worker --candidate eat` command with the same input/support and `--output artifacts/encoder-jin-v1/eat-retry`, inside Python `subprocess.run(..., timeout=600)` with stdout/stderr recorded in `eat-retry.log`. Direct `worker` invocations do not impose their own process timeout. The final code already contains this import repair, so a new campaign should not be expected to reproduce the old technical failure. Preserve original logs and explicit execution notes rather than rewriting them to match a replay.

The final mixture and independent evaluation used:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; & data/ml-runtime/Scripts/python.exe scripts/encoder_experiment.py mixture --members artifacts/encoder-jin-v1/fisher/predictions.json artifacts/encoder-jin-v1/echo/predictions.json artifacts/encoder-jin-v1/eat-retry/predictions.json --output artifacts/encoder-jin-v1/mixture-final.json; if ($LASTEXITCODE) { throw 'Mixture failed' }; & data/ml-runtime/Scripts/python.exe scripts/evaluate_audio.py --references data/jin-directions-v1/sealed/references.json --predictions artifacts/encoder-jin-v1/fisher/predictions.json artifacts/encoder-jin-v1/echo/predictions.json artifacts/encoder-jin-v1/eat-retry/predictions.json artifacts/encoder-jin-v1/mixture-final.json --partition development --output artifacts/encoder-jin-v1/evaluation.json; if ($LASTEXITCODE) { throw 'Evaluation failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

Those outputs also refuse overwrite. All three encoders and the final mixture scored 12/12, macro-F1 1.0. Equal weights were fixed before evaluation; the evaluator's historical tie-break selecting FISHER is not an implemented router. Mixture assembly requires different model IDs and identical support digests, classes, ordered sample IDs, audio hashes and complete accepted coverage. It sums member load/support/query costs and adds measured averaging time; it does not claim that mixing already cached probabilities alone is the inference cost.

Offline aggregate replay uses a new output path and the preserved execution notes. Notes record the actual technical recovery and preliminary mixture, rather than assigning the original timings to new runs. The exporter is scoped to this four-support, twelve-query Jin study. It verifies every prediction/provenance/evaluation hash and every model/configuration/source file hash before exporting:

```powershell
$timer=[Diagnostics.Stopwatch]::StartNew(); try { $env:PYTHONPATH='src'; & data/ml-runtime/Scripts/python.exe scripts/encoder_experiment.py report --members artifacts/encoder-jin-v1/fisher/predictions.json artifacts/encoder-jin-v1/echo/predictions.json artifacts/encoder-jin-v1/eat-retry/predictions.json artifacts/encoder-jin-v1/mixture-final.json --evaluation artifacts/encoder-jin-v1/evaluation.json --campaign artifacts/encoder-jin-v1/campaign.json --notes artifacts/encoder-jin-v1/execution-notes.json --output artifacts/encoder-jin-v1/aggregate-reproduction.json; if ($LASTEXITCODE) { throw 'Evidence export failed' } } finally { Write-Output "elapsed: $($timer.Elapsed.TotalSeconds)s" }
```

The preserved aggregate (`ml/encoder-jin-v1.json`; local-only) was reproduced byte-for-byte. No query-level outputs are exported. Centroid heads are supervised from `simulated_human_from_publisher` support, never registered as teacher silver or sent to operational training. The already examined Jin set cannot validate future learned model selection. No n increase, confidence tuning, autonomous decision agent, online update or production promotion occurred.
