# ModelMetis

ModelMetis tests audio fault classification with foundation models and cheaper specialists trained on their provisional labels.

**The tested teacher-to-specialist approach has not produced useful diagnostic performance.** Frozen encoders and a spectral control scored 12/12 on a small Jin development split, but cross-drone classification remained poor. DSP measurements and images supplied to GPT-5.6 Sol produced 0/9 correct known-condition trials and 3/3 correct unknown-condition rejections. No model is approved for operational diagnosis.

## What We Tested

Public datasets supply microphone recordings and sealed reference labels. Model inputs exclude source filenames, query labels and identifying metadata. Operational specialists use teacher-generated silver labels. One-shot experiments use one disjoint labeled support recording per category, with publisher labels recorded as simulated human annotation. Supervised controls have a separate training path.

| Experiment | Main observation |
| --- | --- |
| Ottawa electric-motor audio, eight classes | Preliminary CLAP teacher: 1/16 correct on final evaluation; silver-trained specialist: 2/16. CLAP is not a generative LLM. Subsequent GPT Audio development results were also poor. |
| AI Mechanic combustion-engine audio, four classes | Fifteen constant recordings were excluded during audit. Best GPT Audio development result: 3/8; specialists trained on eight and eleven silver labels scored 2/8 and 1/8. Normalization and one-shot support did not improve overall accuracy. |
| Jin electric-motor audio, four classes | With the same four labeled support clips and twelve queries, a spectral/logistic supervised control scored 12/12; GPT Audio 1.5 scored 6/12 and missed every healthy and tight-bearing case. |
| Cross-drone audio, nine classes | One A support per class, 54 B queries: forced classification 4-9/54; all three support-only geometric policies abstained on 54/54. One held-out drone, not 54 independent devices. |
| Larger encoders | Dasheng same-condition P@5: 27.41% against a 9.43% random baseline; only 90/751 within-cluster pairs share a condition. Retrieval improved; groups remained impure. |
| STFT-only comparison (EXP-011) | Numerical control abstained on 12/12 trials; visual model inference was not executed. |
| DSP-to-Sol comparison (EXP-012) | All twelve trials returned outside-reference: 9/9 known cases wrongly rejected, 3/3 unknown cases correctly rejected; zero technical failures. Three distinct query clips were reused across folds. |

### Same-Query Comparison On Jin

| Method | Labeled inputs | Correct | Macro-F1 |
| --- | --- | ---: | ---: |
| Welch spectrum + logistic regression | One front recording per class | 12/12 | 1.000000 |
| Welch spectrum + logistic regression | Thirty left-recording windows per class | 12/12 | 1.000000 |
| MFCC + SVM | One front recording per class | 6/12 | 0.446429 |
| MFCC + SVM | Thirty left-recording windows per class | 8/12 | 0.589286 |
| GPT Audio 1.5 | Same one front recording per class | 6/12 | 0.375000 |
| FISHER-small + cosine centroid | Same one front recording per class | 12/12 | 1.000000 |
| ECHO-small + cosine centroid | Same one front recording per class | 12/12 | 1.000000 |
| EAT-base30 + cosine centroid | Same one front recording per class | 12/12 | 1.000000 |
| Uniform three-encoder mixture | Same one front recording per class | 12/12 | 1.000000 |

The spectral control demonstrates class-discriminating signal under this split. The teacher's failure therefore cannot be attributed solely to an absence of usable information in the audio. It does not establish causal fault recognition: the twelve queries come from only four held-out recordings, motor/session independence is undocumented, and acquisition artifacts may distinguish classes. Healthy and faulty source files also use different encodings. The larger training regime changes recording direction as well as label count, so it is not a controlled learning curve. None of these results validates diagnosis on a manufacturer's heavy vehicles.

Experiment reports retain failed attempts, provenance, latency and token-price estimates. No teacher or specialist passed the operational promotion gate.

## Evidence And Reproduction

- [Chronological protocols, failures and results](docs/EXPERIMENTS.md).
- [Dataset audits, licenses and primary literature](docs/AUDIO_DATASETS.md).
- [Jin supervised controls and teacher comparison](ml/jin-directions-v1.json).
- Frozen-encoder results, failed attempts and exact revisions (`ml/encoder-jin-v1.json`; local-only).
- Cross-drone one-shot results and selective coverage (`ml/drone-one-shot-v1.json`; local-only).
- Embedding similarity, larger encoders and all technical attempts (`ml/embedding-geometry-v1.json`; local-only).
- [Deterministic DSP reports](docs/DSP_PIPELINE.md), [STFT-only results](docs/VISUAL_AUDIO_RESULTS.md) and [DSP-to-Sol results](docs/DSP_LLM_RESULTS.md).
- [Cumulative audio attempts and accounting](ml/audio-experiments-20260918-jin.json).
- [Reproduction commands and input boundaries](scripts/README.md).
- [Test scope and limitations](tests/README.md).

Software tests cover workflow and accidental label leakage. Raw recordings, per-example predictions, model weights, sealed labels and credentials are excluded from publication. Filesystem separation is not an OS-enforced security boundary; public-benchmark exposure during pretraining is unknown.

Independent-motor confirmation, autonomous coordination, private cloud training and adaptive routing remain unresolved. The review application is separate from the command-line experiments. See the [current state and constraints](docs/CONTEXT.md).

The original sources are [idea.txt](idea.txt) and [ModelMetis.png](ModelMetis.png), preserved without changes.

## Getting Started

For the experiments, follow the [runtime and reproduction guide](ml/README.md) and [commands](scripts/README.md). The [API setup](apps/api/README.md) is optional and independent of these experiments. Local audio and metadata are stored beneath the ignored `data/local` directory by default. The backend binds to loopback and refuses production mode until real authentication is implemented. It must not be deployed or forwarded to a public interface.

The [plan](docs/PIANO.md), [architecture](docs/ARCHITETTURA.md), [validation protocol](docs/VALIDAZIONE.md) and [backlog](docs/BACKLOG.md) cover the remaining lifecycle work.

## Directories

| Path | Responsibility |
| --- | --- |
| [docs](docs/PIANO.md) | Plan, architecture, validation, and backlog |
| [apps/api](apps/api/README.md) | Inference, feedback, and administration API |
| [apps/console](apps/console/README.md) | Human review and operational dashboard |
| [src/modelmetis](src/modelmetis/README.md) | Domain, routing, datasets, and lifecycle coordination |
| [contracts](contracts/README.md) | Versioned API contracts, events, and manifests |
| [configs](configs/README.md) | Tasks, prompts, and declarative policies, without secrets |
| [ml](ml/README.md) | Data preparation, training, calibration, and evaluation |
| [infra](infra/README.md) | Specification of Bicep modules to implement after approval |
| [tests](tests/README.md) | Test strategy and non-sensitive fixtures |
| [data](data/README.md) | Local data rules and Azure asset references |
| [scripts](scripts/README.md) | Dataset import, experiments, controls and aggregate reporting |
| [.github](.github/README.md) | Specification of future CI/CD pipelines |

## Architecture

The local stack is Python, FastAPI, React and TypeScript. The proposed cloud stack uses Container Apps for API/worker, Microsoft Foundry for teachers, Azure Machine Learning for training, Blob Storage for audio/artifacts, PostgreSQL for state and Service Bus for events. Model endpoints have been used; AML, private storage and GPU execution remain unimplemented. Infrastructure uses IaC, private storage endpoints and managed identities. Promotion and rollback require deterministic, auditable gates. The Windows x64 ML environment has [dependency snapshots](ml/requirements-audio-windows-x64.txt); a cross-platform lockfile is pending.
