# Documentation Map

**Read the method, then the results, then inspect the examples.** Each document owns one responsibility; the others link to it instead of repeating its tables.

## Main Reading Path

| Responsibility | Owner |
| --- | --- |
| Method: inputs, comparison, reference selection, abstention and failure modes | [Method](METHOD.md) |
| Results: verified counts, explanations, selected decisions and limits | [Results](RESULTS.md) |
| Examples: audio, figures, exact model inputs and decisions | [Public examples](../examples/README.md) |
| Reproduction: verification, regeneration and paid-inference boundaries | [Reproduction guide](../scripts/README.md) |

## Technical Records Of The Simple Method

| Responsibility | Owner |
| --- | --- |
| DSP definitions and measurement limits | [DSP pipeline](DSP_PIPELINE.md) |
| Request contract, folders and admission limits | [Whole-report comparison](DSP_REPORT_COMPARISON.md) |
| Dataset selection, calibration, gates and every technical attempt | [Labeled results record](DSP_LABELED_RESULTS.md) |
| Exact recorded code versions | [Registered code](../registered/simple-method/README.md) |
| Human listening workbench and its versions | [Human audio comparison](HUMAN_AUDIO_COMPARISON.md) |
| Rights, acquisition grouping and external scores | [Datasets](AUDIO_DATASETS.md), [benchmark status](DSP_BENCHMARK_STATUS.md) |
| Released and withheld material | [Publication policy](PUBLICATION.md) |

## Archived Variants And Earlier Studies

The first six rows came after the simple method and did not improve safety; the last row preceded it. All keep their protocols, measurements and negative findings.

| Variant | Protocol | Measured result |
| --- | --- | --- |
| Offline multi-reference representations | [Offline protocol](DSP_OFFLINE_PROTOCOL.md) | [Offline results](DSP_OFFLINE_RESULTS.md) |
| All 26 diagrams | [Extensions](DSP_EXTENSIONS.md) | [Extensions](DSP_EXTENSIONS.md) |
| Diagram attribution | [Attribution audit](DSP_DIAGRAM_AUDIT.md) | [Attribution audit](DSP_DIAGRAM_AUDIT.md) |
| Family separation without a model | [Family separation](DSP_FAMILY_SEPARATION.md) | [Family separation](DSP_FAMILY_SEPARATION.md) |
| Removing diagram types | [Pruning protocol](DSP_PRUNING_PROTOCOL.md) | [Pruning results](DSP_PRUNING_RESULTS.md) |
| Aggregated class cards with adaptive memory | [Memory protocol](DSP_MEMORY_PROTOCOL.md) | [Memory results](DSP_MEMORY_RESULTS.md) |
| Single-image FFT/STFT packets and earlier model studies | [EXP-012 format](DSP_LLM_FORMAT.md), [protocol](DSP_LLM_PROTOCOL.md) | [EXP-012 results](DSP_LLM_RESULTS.md), [experiment archive](EXPERIMENTS.md), [historical commands](LEGACY_COMMANDS.md) |

## Development

[Maintainer state](CONTEXT.md) owns gates, data boundaries and runtime constraints. [Architecture](ARCHITETTURA.md), [backlog](BACKLOG.md), [validation](VALIDAZIONE.md) and [resource reuse](DSP_RESOURCE_REUSE.md) describe proposed or infrastructure work.

Public artifacts live under `examples/`. Paths under `outputs/`, `artifacts/` and `data/` identify local source material that a clone does not contain; they are unnecessary for inspecting the public snapshot.
