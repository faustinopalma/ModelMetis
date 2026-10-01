# ModelMetis

**A multimodal model can recognize a machine condition by comparing the signal-processing report of an unknown recording with reports of recordings whose condition is known, provided the references represent that condition.** With reports plus spectral distances it recognized 11 of 12 reserved Jin motor windows and correctly rejected 2 of 4 tests whose class was missing. With one reference per class recorded under another operating profile, it recognized only 4 of 16 Ottawa motor acquisitions. This is research evidence, not an approved diagnostic.

[Open the method and results page](https://faustinopalma.github.io/ModelMetis/) or [listen to every recorded decision](https://faustinopalma.github.io/ModelMetis/audio-comparison/) beside its references.

## How The Method Works

1. **Measure.** Each ten-second recording becomes a deterministic DSP report: seven diagrams of the interval, a complete-recording overview and their numerical measurements.
2. **Supply references.** One report per known condition, from a recording selected before testing.
3. **Compare.** The model compares the unknown report with every reference and must cite evidence from both.
4. **Decide or abstain.** It names the best-supported known condition, or answers `different`, which sends the case to a person.

The model never receives audio; the audio is published so people can listen. References are part of the method: each must resemble its condition as it will be recorded, and a label whose recordings behave very differently needs one reference per acoustic family or operating regime. The [method](docs/METHOD.md) explains inputs, abstention, reference selection and failure modes.

## What The Recorded Experiments Show

| Data | Configuration | Class present | Class excluded |
| --- | --- | --- | --- |
| Jin, 12 reserved right-microphone windows | Reports plus Welch distances | 11/12 correct, 1 false rejection | 2/4 correctly rejected, 2 wrong acceptances |
| Same Jin windows, exploratory replay | Calibrated distance rule | 9/12 correct, 3 false rejections | 4/4 correctly rejected |
| Ottawa, 16 profile-2 acquisitions | Reports only | 4/16 correct, 12 wrong classes | Not tested |

Rows are separate configurations; do not combine them. Forced nearest distance alone also labels all 12 Jin windows correctly, so the model's added accuracy is unproven. The failures have recognizable causes: references that miss an operating regime, references that lie close together and explanations that override the numbers. [Results](docs/RESULTS.md) give denominators, distances, six inspectable decisions and limits. Later variants with more diagrams, fewer diagrams or adaptive class memory did not improve safety and are [archived](docs/RESULTS.md#later-variants-are-archived-limits).

## Find What You Need

| Need | Go to |
| --- | --- |
| Understand the method | [Method](docs/METHOD.md) |
| Check measured results and limits | [Results](docs/RESULTS.md) |
| Listen to and inspect recorded decisions | [Public examples](examples/README.md) |
| Verify or reproduce the evidence | [Reproduction guide](scripts/README.md) |
| Find any other document | [Documentation map](docs/README.md) |
| Reuse the audio | [Attribution](examples/audio-comparison/ATTRIBUTION.md) and [publication policy](docs/PUBLICATION.md) |

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

The experiments use two public motor datasets, publisher condition labels and few acquisitions. The recordings were used in earlier project experiments, physical machines recur and recording regimes change, so the numbers do not establish general reliability, state of the art or human parity. Published scores from other models use different sensors, splits or label budgets; they are declared reference points, not comparable results. Valid citations and successful requests are technical checks, not proof of correctness.

The public examples are truth-visible review material, not blind human trials or a clean final evaluation. Complete source archives, credentials, runtime caches, unselected requests and intermediate runs remain excluded. Public audio derivatives retain their source CC BY 4.0 attribution; no blanket software license is implied by those dataset terms.

## Develop Or Explore Further

The [documentation map](docs/README.md) separates method, results, examples, reproduction and archived studies. [Maintainer state](docs/CONTEXT.md) records development gates and data boundaries. The [local API](apps/api/README.md) and [console](apps/console/README.md) are separate prototypes, not the public demonstration or an approved diagnostic service.

Earlier teacher/specialist, encoder and cross-drone studies remain in the [experiment archive](docs/EXPERIMENTS.md); their findings motivated the DSP work and are not a shared leaderboard. The original [idea](idea.txt) and [diagram](ModelMetis.png) are preserved.
