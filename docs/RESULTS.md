# The Simple Method Recognizes Jin Conditions But Fails Across Ottawa Operating Profiles

**With DSP reports plus Welch distances, the model recognized 11 of 12 reserved Jin windows and correctly rejected 2 of 4 excluded-class tests; with reports only, it recognized 4 of 16 Ottawa profile-2 acquisitions.** An exploratory calibrated replay on the same Jin inputs traded recognition for rejection: 9 of 12 and 4 of 4. These are separate configurations; never combine their best numbers. A forced nearest-distance rule already labels all 12 reserved Jin windows correctly, so an added benefit of the model is not demonstrated. No general reliability, state-of-the-art or human-parity claim is made.

[Listen to every decision](https://faustinopalma.github.io/ModelMetis/audio-comparison/) beside its references, or inspect the [local snapshot](../examples/README.md). The [method](METHOD.md) defines inputs, abstention and reference selection; the [labeled-results record](DSP_LABELED_RESULTS.md) keeps dataset, calibration and attempt details.

## Results Are Reported Per Configuration

| Data | Configuration | Correct class | Wrong class | False rejection | Correct rejection, class excluded | Wrong acceptance, class excluded |
| --- | --- | --- | --- | --- | --- | --- |
| Jin development, 8 left-microphone windows | A, reports only | 5/8 | 3/8 | 0/8 | Not tested | Not tested |
| Jin development, same 8 windows | B, reports plus distances | 8/8 | 0/8 | 0/8 | Not tested | Not tested |
| Jin reserved, 12 right-microphone windows | B, reports plus distances | 11/12 | 0/12 | 1/12 | 2/4 | 2/4 |
| Jin reserved, same windows, exploratory replay | C, calibrated rule | 9/12 | 0/12 | 3/12 | 4/4 | 0/4 |
| Ottawa development, 16 profile-2 acquisitions | A, reports only | 4/16 | 12/16 | 0/16 | Not tested | Not tested |

Publisher labels are the ground truth. Configuration B passed the Jin development gate (at least 7 of 8, one per class) and was selected before the reserved windows were run. Its reserved gate required 11 of 12 recognitions and 4 of 4 rejections: it met the first and failed the second. Ottawa failed its 14-of-16 development gate, so configuration B and Ottawa's reserved profile-8 acquisitions were never run under this method. Excluded-class tests use the first window of each Jin class, T01, T04, T07 and T10, with its own reference removed.

The study made 68 HTTP attempts: 64 decisions and 4 technical failures (one image-count rejection, two token-rate rejections, one truncated completion). Technical failures are excluded from the denominators and listed with every decision in the [published outcome record](../examples/results/simple-method-outcomes.json).

## Distances Explain Where Jin Works And Fails

The Welch distances below were supplied to the model in configurations B and C. Each class's right-microphone windows lie near its front-microphone reference, except magnet fracture.

| Reserved windows | Distance to own reference | Nearest other reference | Configuration B |
| --- | --- | --- | --- |
| Excess Hall adhesive, T01-T03 | 2.98-3.15 dB | 7.38 dB or more | 3/3 correct |
| Healthy, T04-T06 | 3.02-3.12 dB | 6.35 dB or more | 3/3 correct |
| Magnet fracture, T07-T09 | 3.62-3.68 dB | Tight bearing, 3.72-3.76 dB | 2/3 correct, T07 rejected |
| Tight bearing, T10-T12 | 2.21-2.26 dB | Magnet fracture, 3.89-3.92 dB | 3/3 correct |

The magnet-fracture and tight-bearing references are only 3.04 dB apart, closer than magnet-fracture windows are to their own reference. That geometry explains three outcomes: configuration B missed T07; configuration C's 3.23 dB magnet-fracture threshold rejected all three magnet windows; and with the magnet reference removed, T07 was accepted as tight bearing at 3.72 dB. The method's remedy is a reference that represents that regime, chosen without test outcomes. It was not tested, and a looser threshold would admit more wrong acceptances.

The healthy excluded-class test T04 shows a second failure. Its nearest remaining reference, tight bearing, was 6.35 dB away. The model acknowledged that this exceeded the 3.04 dB reference separation, then accepted tight bearing because level, crest factor and a 16 kHz ridge looked similar. T01 at 7.62 dB and T10 at 3.92 dB were rejected, so configuration B applied no consistent distance limit.

## Ottawa Fails Because References Do Not Represent Profile 2

The model never abstained on Ottawa. It recognized both healthy acquisitions, one stator-winding and one bowed-rotor acquisition; its twelve wrong answers were seven stator winding, four bowed rotor and one rotor misalignment. Nearest Welch distance alone labels 2 of 16 correctly, 3 of 16 using only bins above 2 kHz, so profile-2 recordings already lie nearer other classes' profile-1 references. The later [family analysis](DSP_FAMILY_SEPARATION.md) found no Ottawa class separated from all others across profiles in any tested representation. References for each operating profile and load are a prerequisite before another model test.

## Inspect Six Recorded Decisions

Each link opens the audio, all eight figures and the recorded explanation; the evidence column links the exact parsed decision and model input in this repository.

| Decision | Outcome | Evidence | What it shows |
| --- | --- | --- | --- |
| [Jin T01, reserved](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-reserved-T01) | Correct, excess Hall adhesive | [decision](../examples/audio-comparison/responses/jin-distances-reserved-T01.json), [input](../examples/audio-comparison/inputs/jin-distances-reserved-T01.json) | Clear separation transfers from front to right microphone |
| [Jin T01, class excluded](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-excluded-T01) | Correct `different` | [decision](../examples/audio-comparison/responses/jin-distances-excluded-T01.json), [input](../examples/audio-comparison/inputs/jin-distances-excluded-T01.json) | The same window is rejected when its reference is withheld |
| [Jin T07, reserved](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-reserved-T07) | False rejection | [decision](../examples/audio-comparison/responses/jin-distances-reserved-T07.json), [input](../examples/audio-comparison/inputs/jin-distances-reserved-T07.json) | Close magnet-fracture and tight-bearing references |
| [Jin T04, class excluded](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-excluded-T04) | Wrong acceptance, tight bearing | [decision](../examples/audio-comparison/responses/jin-distances-excluded-T04.json), [input](../examples/audio-comparison/inputs/jin-distances-excluded-T04.json) | The model argues past a large distance |
| [Ottawa D01](https://faustinopalma.github.io/ModelMetis/audio-comparison/#ottawa-reports-development-D01) | Correct, healthy | [decision](../examples/audio-comparison/responses/ottawa-reports-development-D01.json), [input](../examples/audio-comparison/inputs/ottawa-reports-development-D01.json) | Recognition across profiles can work |
| [Ottawa D03](https://faustinopalma.github.io/ModelMetis/audio-comparison/#ottawa-reports-development-D03) | Wrong, stator winding for rotor unbalance | [decision](../examples/audio-comparison/responses/ottawa-reports-development-D03.json), [input](../examples/audio-comparison/inputs/ottawa-reports-development-D03.json) | One reference per class misses the profile change |

## What These Results Do Not Show

- **Fresh evaluation.** Both public datasets were used in earlier project experiments; no blind or fresh final evaluation has been run.
- **Many independent machines.** The 12 reserved Jin windows come from four acquisitions, three windows each, and original healthy/fault files differ in PCM16/FLOAT encoding. Ottawa motors recur across profiles, so motor identity can be confounded with class.
- **New faults.** Excluded-class tests remove a known reference; they do not present genuinely new fault mechanisms.
- **Model benefit over numbers.** Forced nearest distance labels the reserved Jin windows as well as the model; the model adds cited explanations and the possibility of abstention, not demonstrated accuracy.
- **Comparability with published scores.** External scores in [benchmark status](DSP_BENCHMARK_STATUS.md) use other sensors, splits or label budgets; they are declared reference points, not reproduced comparisons.
- **Frozen software.** The runner and validator evolved during the study. [Registered code](../registered/simple-method/README.md) preserves the recovered recorded versions; one similarity-module version used by configuration A was not preserved, while its exact requests and responses were.

## Later Variants Are Archived Limits

Later studies changed the input or the reference representation to address these failures. None improved safety. They use different inputs and must not be pooled with the table above; the [archive page](https://faustinopalma.github.io/ModelMetis/archive/) publishes their selected evidence.

| Variant | Measured observation | Owner |
| --- | --- | --- |
| All 26 diagrams, adding 19 analyses | 6/12 correct, 4/12 wrong, 2/12 false rejections; 4/12 correct and 8/12 wrong excluded-class answers | [All-diagram results](DSP_EXTENSIONS.md) |
| Explicit review of every diagram | 8 paired decisions stay 5/8 correct; wrong assignments fall from 2/8 to 0/8 while false rejections rise from 1/4 to 3/4 | [Attribution audit](DSP_DIAGRAM_AUDIT.md) |
| Removing three diagram types | Primary cases improve from 5/8 to 6/8, but an identical repeated request gives a wrong class | [Pruning results](DSP_PRUNING_RESULTS.md) |
| Aggregated class cards with adaptive memory, 72 Ottawa acquisitions | Fixed: 16 correct, 11 wrong, 45 review. Adaptive: 18 correct, 41 wrong, 13 review | [Class-memory results](DSP_MEMORY_RESULTS.md) |
| Family separation without a model | Full spectra and cepstrum group 12/12 Jin acquisitions; Ottawa's best whole-profile result is 9/24 | [Family separation](DSP_FAMILY_SEPARATION.md) |

Earlier encoder, teacher/specialist and cross-drone studies remain in the [experiment archive](EXPERIMENTS.md). [Publication policy](PUBLICATION.md) defines what is released.
