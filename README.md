# ModelMetis

**ModelMetis recognizes machine conditions from audio: it turns each recording into signal-processing diagrams and measurements, and a general multimodal model compares them with recordings of known conditions.** With reports plus spectral distances it recognized 11 of 12 reserved Jin motor windows and correctly set aside 2 of 4 cases whose condition had no reference. On Ottawa motors, whose references come from another speed and load profile, it recognized 4 of 16 acquisitions; references for every operating regime are the current focus.

[Open the method and results page](https://faustinopalma.github.io/ModelMetis/) or [listen to every recorded decision](https://faustinopalma.github.io/ModelMetis/audio-comparison/) beside its references.

## How The Method Works

1. **Analyze.** The system receives the audio and computes a deterministic DSP report for each ten-second recording: seven diagrams of the interval, a complete-recording overview and their numerical measurements.
2. **Supply references.** Each known condition contributes one report, from a recording selected before testing.
3. **Compare.** A general multimodal model studies the unknown report beside every reference and cites evidence from both.
4. **Decide.** The model names the best-supported known condition, or answers `different` so that a person reviews the case.

Every recording is published with its diagrams, so a person can listen to an unknown sample and each reference side by side. Good references drive good decisions: each resembles its condition as it will be recorded, and a label whose recordings behave very differently gets one reference per acoustic family or operating regime. The [method](docs/METHOD.md) explains inputs, decisions, reference selection and the patterns we are improving.

## What The Recorded Experiments Show

| Data | Configuration | Class present | Class excluded |
| --- | --- | --- | --- |
| Jin, 12 reserved right-microphone windows | Reports plus Welch distances | 11/12 correct, 1 set aside | 2/4 correctly set aside, 2 wrong acceptances |
| Same Jin windows, exploratory replay | Calibrated distance rule | 9/12 correct, 3 set aside | 4/4 correctly set aside |
| Ottawa, 16 profile-2 acquisitions | Reports only | 4/16 correct, 12 wrong classes | Not tested |

Each row is one configuration with its own counts. Nearest Welch distance alone also labels all 12 Jin windows, and the next comparisons measure what the model adds beyond these numbers. The remaining errors follow three patterns: references from another operating regime, references that lie close together and explanations that drift from the numbers. [Results](docs/RESULTS.md) give denominators, distances, six inspectable decisions and the current scope. More diagrams, fewer diagrams and an adaptive class memory were also [explored](docs/RESULTS.md#other-directions-explored).

## Find What You Need

| Need | Go to |
| --- | --- |
| Understand the method | [Method](docs/METHOD.md) |
| Check measured results and scope | [Results](docs/RESULTS.md) |
| Listen to and inspect recorded decisions | [Public examples](examples/README.md) |
| Verify or reproduce the evidence | [Reproduction guide](scripts/README.md) |
| Find any other document | [Documentation map](docs/README.md) |
| Reuse the audio | [Attribution](examples/audio-comparison/ATTRIBUTION.md) and [publication policy](docs/PUBLICATION.md) |

## Verify A Clone Locally

Audio, plots, selected model answers and structured evidence are included as local files. To verify a clone with Python 3.12 or later and the standard library:

```console
python -m scripts.check_examples
python -m scripts.check_publication
```

Re-running numerical analysis or a new inference campaign has its own dependencies and inputs, listed in the [reproduction guide](scripts/README.md).

For local browsing, serve the static snapshot and open `http://127.0.0.1:8000/`:

```console
python -m http.server 8000 --bind 127.0.0.1 --directory examples
```

HTTP serving lets every browser play the WAV files; some integrated browsers block audio opened from `file://`.

## Scope And Next Steps

The experiments use two public motor datasets, publisher condition labels and few acquisitions that the project has already studied; physical machines recur and recording regimes change. Fresh recordings, references for every operating regime and blind listening comparisons are the next steps. Published scores from other models use their own sensors, splits and label budgets and serve as context. Citation checks and successful requests confirm well-formed answers; correctness is scored against publisher labels.

Publisher labels are shown with every example so each decision can be checked. Source archives, credentials, runtime caches, unselected requests and intermediate runs stay private. Public audio derivatives keep their source CC BY 4.0 attribution; dataset terms apply to the audio, and the code license is a separate decision.

## Develop Or Explore Further

The [documentation map](docs/README.md) separates method, results, examples, reproduction and other explored directions. [Maintainer state](docs/CONTEXT.md) records development gates and data boundaries. The [local API](apps/api/README.md) and [console](apps/console/README.md) are separate prototypes for audio review.

Earlier teacher/specialist, encoder and cross-drone studies, which motivated the DSP work, remain in the [experiment archive](docs/EXPERIMENTS.md). The original [idea](idea.txt) and [diagram](ModelMetis.png) are preserved.
