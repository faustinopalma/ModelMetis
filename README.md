# ModelMetis

**Audio fault classification is not yet reliable enough for autonomous diagnosis.** ModelMetis investigates how foundation models use signal-processing evidence, when they assign a wrong condition, and whether removing misleading inputs improves recognition without sacrificing safe abstention.

Start with the [interactive audio comparison](https://faustinopalma.github.io/ModelMetis/audio-comparison/), the [evidence explorer](https://faustinopalma.github.io/ModelMetis/) or the [measured results](docs/RESULTS.md). The same static pages are included under [examples](examples/README.md) and work locally without an account, backend or model call.

## Inspect The Evidence

The current public snapshot includes sixteen attributed audio excerpts, paired DSP figures, ten recorded decisions from the tested pruning candidate, the complete forty-six-decision crossed-study matrix and family-separation comparisons. It deliberately includes the unsafe repeat, successful recognition and correct rejection. The candidate remains unapproved; no state-of-the-art or human-parity claim is made.

| Question | Read or run |
| --- | --- |
| What worked, failed and remains uncertain? | [Results](docs/RESULTS.md) |
| What evidence did the model receive, and what did it choose? | [Audio comparison](examples/audio-comparison/README.md) |
| Which representations remain stable within a family? | [Family separation](docs/DSP_FAMILY_SEPARATION.md) |
| Does removing error-associated evidence help? | [Pruning strategy](docs/DSP_PRUNING_PROTOCOL.md) and [measured effects](docs/DSP_PRUNING_RESULTS.md) |
| Can these results be called state of the art? | [Benchmark and human-baseline status](docs/DSP_BENCHMARK_STATUS.md) |
| How do I verify or reproduce the work? | [Supported commands](scripts/README.md) |
| What may be redistributed? | [Publication policy](docs/PUBLICATION.md) and [audio attribution](examples/audio-comparison/ATTRIBUTION.md) |

## Verify Without Cloud Access

Audio, plots, selected model answers and structured evidence are included as local files. To verify a clone with Python 3.12 or later:

```console
python -m scripts.check_examples
python -m scripts.check_publication
```

These commands make no inference calls and require no model credentials. Re-running numerical analysis or generating a new inference campaign has separate dependencies and explicit input requirements in the [reproduction guide](scripts/README.md).

For local browsing, serve the static snapshot and open `http://127.0.0.1:8000/`:

```console
python -m http.server 8000 --bind 127.0.0.1 --directory examples
```

Some integrated browsers block external WAV files on `file://`; HTTP avoids that restriction. This server serves files only and exposes no inference API.

## Scope And Boundaries

The experiments use public motor/engine recordings and publisher condition labels. Small acquisition counts, shared physical machines, changed recording regimes and potential benchmark exposure limit generalization. Correct schema, valid citations and successful requests are technical checks; they are not proof of diagnostic correctness. False rejections, wrong assignments and unavailable evidence are reported separately.

The public examples are consumed, truth-visible review material. They cannot serve as blind human trials or clean final model evaluation. Complete source archives, credentials, runtime caches, unselected requests and intermediate runs remain excluded. Public audio derivatives retain their source CC BY 4.0 attribution; no blanket software license is implied by those dataset terms.

## Develop Or Explore Further

[Documentation map](docs/README.md) separates methods, datasets, evidence, implementation and archived studies. [Maintainer state](docs/CONTEXT.md) records the next development gates without duplicating result tables. The [local API](apps/api/README.md) and [console](apps/console/README.md) are separate prototypes, not the public static demonstration or an approved diagnostic service.

Earlier teacher/specialist, encoder and cross-drone studies remain in the [experiment archive](docs/EXPERIMENTS.md). Their negative and limited positive findings motivated the current DSP work; they are not a shared benchmark leaderboard. The original [idea](idea.txt) and [diagram](ModelMetis.png) are preserved.
