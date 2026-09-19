# ModelMetis

ModelMetis investigates whether a general audio-capable model can label initially unlabeled motor recordings well enough to train cheaper specialists. The intended benefit is lower inference cost without unacceptable loss of diagnostic quality. This is an experimental hypothesis, not an established capability.

**Result published September 19, 2026: the approach has not worked in the experiments conducted so far.** The teacher's labels were not sufficiently accurate, and specialists trained on those labels did not show useful improvement. More labels from the same teacher are not justified by this evidence. This does not prove that every teacher or every version of the architecture must fail.

## What We Tested

Experiments ran on September 18, 2026. Public datasets supplied real microphone recordings and separately held reference labels. Model inputs excluded source filenames, query labels and identifying metadata. Operational specialists received teacher-generated silver labels only. Later one-shot experiments explicitly disclosed one disjoint labeled support recording per category, simulating human annotation. Publisher-supervised controls were isolated from the operational training path.

| Experiment | Main observation |
| --- | --- |
| Ottawa electric-motor audio, eight classes | Preliminary CLAP teacher: 1/16 correct on final evaluation; silver-trained specialist: 2/16. CLAP is not a generative LLM. Subsequent GPT Audio development results were also poor. |
| AI Mechanic combustion-engine audio, four classes | Fifteen constant recordings were excluded during audit. Best GPT Audio development result: 3/8; specialists trained on eight and eleven silver labels scored 2/8 and 1/8. Normalization and one-shot support did not improve overall accuracy. |
| Jin electric-motor audio, four classes | With the same four labeled support clips and twelve queries, a spectral/logistic supervised control scored 12/12; GPT Audio 1.5 scored 6/12 and missed every healthy and tight-bearing case. |

The [supervised literature review](docs/AUDIO_DATASETS.md#september-18-supervised-literature-review) preceded the Jin experiment. Published audio-only results range from 99.54% classification accuracy on laboratory MAFAULDA data to substantially weaker automotive event-detection results. These tasks and metrics are not directly comparable, and our controls do not reproduce either publication.

### Same-Query Comparison On Jin

| Method | Labeled inputs | Correct | Macro-F1 |
| --- | --- | ---: | ---: |
| Welch spectrum + logistic regression | One front recording per class | 12/12 | 1.000000 |
| Welch spectrum + logistic regression | Thirty left-recording windows per class | 12/12 | 1.000000 |
| MFCC + SVM | One front recording per class | 6/12 | 0.446429 |
| MFCC + SVM | Thirty left-recording windows per class | 8/12 | 0.589286 |
| GPT Audio 1.5 | Same one front recording per class | 6/12 | 0.375000 |

The spectral control demonstrates class-discriminating signal under this split. The teacher's failure therefore cannot be attributed solely to an absence of usable information in the audio. It does not establish causal fault recognition: the twelve queries come from only four held-out recordings, motor/session independence is undocumented, and acquisition artifacts may distinguish classes. Healthy and faulty source files also use different encodings. The larger training regime changes recording direction as well as label count, so it is not a controlled learning curve. None of these results validates diagnosis on a manufacturer's heavy vehicles.

The teacher failed the preregistered quality threshold. No additional silver collection, operational specialist training or routing promotion followed. All attempts, including failures and inferior control results, are retained. Sixteen live audio attempts reconcile to 129 request reservations and 128 responses with known usage; estimated list-price consumption is USD 0.8541325, including USD 0.21281 for Jin. These are token-price estimates, not invoices or total project costs. A historical unknown-usage request retains a separate conservative reservation, documented in the report.

## Evidence And Reproduction

- [Chronological protocols, failures and results](docs/EXPERIMENTS.md).
- [Dataset audits, licenses and primary literature](docs/AUDIO_DATASETS.md).
- [Jin supervised controls and teacher comparison](ml/jin-directions-v1.json).
- [Cumulative audio attempts and accounting](ml/audio-experiments-20260918-jin.json).
- [Reproduction commands and input boundaries](scripts/README.md).
- [Test scope and limitations](tests/README.md).

Validation on September 18: 104 Python tests passed with no skips and two existing dependency deprecation warnings; Ruff passed. Software tests check the workflow and accidental label-leakage boundaries, not diagnostic competence. Raw recordings, per-example predictions, model weights, sealed labels and credentials are not published. Separate local processes and files are not an OS-enforced security boundary. Public-benchmark exposure during foundation-model pretraining is unknown.

The intended lifecycle remains teacher labeling, silver collection, specialist training, independent evaluation and conditional lower-cost routing. Command-line experiments cover labeling, fitting and evaluation, but competent operational labeling, the autonomous strategy coordinator, private cloud training and adaptive routing remain unresolved. This publication includes the Python experiment toolkit, prompts, review API and tests. The separately developed console and local deployment templates are not included in this publication. The review application is separate from the experiment pipeline; it must not be treated as a production diagnostic service. Start or resume from the [working context](docs/CONTEXT.md).

The original sources are [idea.txt](idea.txt) and [ModelMetis.png](ModelMetis.png), preserved without changes.

## Getting Started

For the experiments, follow the [runtime and reproduction guide](ml/README.md) and [commands](scripts/README.md). The [API setup](apps/api/README.md) is optional and independent of these experiments. Local audio and metadata are stored beneath the ignored `data/local` directory by default. The backend binds to loopback and refuses production mode until real authentication is implemented. It must not be deployed or forwarded to a public interface.

The existing documents describe the broader lifecycle roadmap, originally scoped to images; the measured experiments now concern audio. Roadmap entries are not claims that those components are implemented or validated.

1. Read the [development plan](docs/PIANO.md), which defines the PoC scope and phase sequence.
2. Use the [Azure architecture](docs/ARCHITETTURA.md) to assign components and prepare infrastructure decisions.
3. Agree on the [validation protocol](docs/VALIDAZIONE.md) before selecting models or thresholds.
4. Start with the P0 items in the [backlog](docs/BACKLOG.md). Do not start with training or full provisioning.

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

## Initial Decisions

The PoC covers industrial audio fault classification, one task, and one organization, initially using public electric-motor recordings as a proxy. Python for the runtime and ML, FastAPI for the API, and React and TypeScript for the console. The proposed Azure architecture uses Container Apps for the API and worker, Microsoft Foundry for the teacher, and Azure Machine Learning for training, experiments, and models. Blob Storage would hold audio and artifacts, PostgreSQL metadata and state, and Service Bus events. All resources must be created through IaC in dedicated resource groups; storage requires private endpoints and disabled public access. Only the dedicated, Entra-authenticated Azure audio model endpoint was deployed for these experiments; no AML workspace, storage or GPU was created.

These are design decisions, not proof of an operational cloud lifecycle. The measured Windows x64 ML environment has [dependency snapshots](ml/requirements-audio-windows-x64.txt), not a cross-platform lockfile. No multi-agent framework is introduced into the inference path: safety and promotion decisions must be deterministic and auditable.
