# Documentation Map

**Begin with the results and the public examples.** Detailed study reports own their measurements; this map and the repository README provide navigation rather than repeating those tables.

| Area | Responsibility | Entry point |
| --- | --- | --- |
| Findings | Current conclusions and decisive limitations | [Results](RESULTS.md) |
| Inspection | Audio, selected responses, figures and attribution | [Public examples](../examples/README.md) |
| Signal processing | Numerical definitions and representation limits | [DSP pipeline](DSP_PIPELINE.md), [extensions](DSP_EXTENSIONS.md) |
| Experimental design | Frozen questions, removals and evaluation boundaries | [Pruning protocol](DSP_PRUNING_PROTOCOL.md), [offline protocol](DSP_OFFLINE_PROTOCOL.md) |
| Study detail | Measured family separation, attribution and removal effects | [Family separation](DSP_FAMILY_SEPARATION.md), [attribution](DSP_DIAGRAM_AUDIT.md), [pruning](DSP_PRUNING_RESULTS.md) |
| Sources and validity | Rights, acquisition grouping, benchmarks and human comparison | [Datasets](AUDIO_DATASETS.md), [benchmark status](DSP_BENCHMARK_STATUS.md) |
| Reproduction | Setup, verification and local/paid boundaries | [Commands](../scripts/README.md) |
| Publication | Included, omitted and checked evidence | [Publication policy](PUBLICATION.md) |
| Development | Current gates and proposed lifecycle capabilities | [Maintainer state](CONTEXT.md), [architecture](ARCHITETTURA.md), [backlog](BACKLOG.md) |
| Archive | Earlier experiments and their original limits | [Experiment archive](EXPERIMENTS.md), [historical commands](LEGACY_COMMANDS.md) |

Public artifacts live under `examples/`. Paths under `outputs/`, `artifacts/` and `data/` in detailed reproduction sections identify local source material, not files supplied by a clone. They are unnecessary for inspecting the public snapshot.
