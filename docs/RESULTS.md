# The Simple Method Recognizes Jin Conditions; Ottawa Shows Which References To Add Next

**With DSP reports plus Welch distances, the model recognized 11 of 12 reserved Jin windows and correctly set aside 2 of 4 cases whose condition had no reference; with reports only, it recognized 4 of 16 Ottawa profile-2 acquisitions.** An exploratory calibrated replay on the same Jin inputs shifted the balance toward review: 9 of 12 recognized and 4 of 4 set aside. Each configuration keeps its own counts. Nearest Welch distance alone also labels all 12 reserved Jin windows, so the next comparisons measure what the model adds beyond these numbers.

[Listen to every decision](https://faustinopalma.github.io/ModelMetis/audio-comparison/) beside its references, or inspect the [local snapshot](../examples/README.md). The [method](METHOD.md) defines inputs, decisions and reference selection; the [labeled-results record](DSP_LABELED_RESULTS.md) keeps dataset, calibration and attempt details.

## Results Are Reported Per Configuration

| Data | Configuration | Correct class | Wrong class | False rejection | Correct rejection, class excluded | Wrong acceptance, class excluded |
| --- | --- | --- | --- | --- | --- | --- |
| Jin development, 8 left-microphone windows | A, reports only | 5/8 | 3/8 | 0/8 | Not tested | Not tested |
| Jin development, same 8 windows | B, reports plus distances | 8/8 | 0/8 | 0/8 | Not tested | Not tested |
| Jin reserved, 12 right-microphone windows | B, reports plus distances | 11/12 | 0/12 | 1/12 | 2/4 | 2/4 |
| Jin reserved, same windows, exploratory replay | C, calibrated rule | 9/12 | 0/12 | 3/12 | 4/4 | 0/4 |
| Ottawa development, 16 profile-2 acquisitions | A, reports only | 4/16 | 12/16 | 0/16 | Not tested | Not tested |

Publisher labels are the ground truth. Configuration B passed the Jin development gate (at least 7 of 8, one per class) and was selected before the reserved windows were run. Its reserved gate asked for 11 of 12 recognitions and 4 of 4 correct rejections: it reached the first and 2 of 4 on the second. Ottawa stayed below its 14-of-16 development gate, so its reserved profile-8 acquisitions and configuration B are still to be run there. Excluded-class tests use the first window of each Jin class, T01, T04, T07 and T10, with its own reference withheld.

The study made 68 HTTP attempts: 64 decisions and 4 technical failures (one image-count rejection, two token-rate rejections, one truncated completion). Technical failures are excluded from the denominators and listed with every decision in the [published outcome record](../examples/results/simple-method-outcomes.json).

## Distances Explain The Jin Decisions

The Welch distances below were supplied to the model in configurations B and C. Each class's right-microphone windows lie near its front-microphone reference, except magnet fracture.

| Reserved windows | Distance to own reference | Nearest other reference | Configuration B |
| --- | --- | --- | --- |
| Excess Hall adhesive, T01-T03 | 2.98-3.15 dB | 7.38 dB or more | 3/3 correct |
| Healthy, T04-T06 | 3.02-3.12 dB | 6.35 dB or more | 3/3 correct |
| Magnet fracture, T07-T09 | 3.62-3.68 dB | Tight bearing, 3.72-3.76 dB | 2/3 correct, T07 rejected |
| Tight bearing, T10-T12 | 2.21-2.26 dB | Magnet fracture, 3.89-3.92 dB | 3/3 correct |

The magnet-fracture and tight-bearing references lie only 3.04 dB apart, closer than magnet-fracture windows lie to their own reference. That geometry explains three outcomes: configuration B set T07 aside; configuration C's 3.23 dB magnet-fracture threshold set all three magnet windows aside; and with the magnet reference withheld, T07 was accepted as tight bearing at 3.72 dB. A reference that represents the magnet-fracture regime, chosen without test outcomes, is the natural next step; widening the threshold would admit more wrong acceptances.

The healthy excluded-class test T04 shows a second pattern. Its nearest remaining reference, tight bearing, was 6.35 dB away. The model acknowledged that this exceeded the 3.04 dB reference separation, then accepted tight bearing because level, crest factor and a 16 kHz ridge looked similar. T01 at 7.62 dB and T10 at 3.92 dB were set aside, so configuration B applied its distance guidance case by case; aligning explanations with the numbers is part of the current work.

## Ottawa Shows That References Must Match The Operating Profile

On Ottawa the model always named a class. It recognized both healthy acquisitions, one stator-winding and one bowed-rotor acquisition; its twelve wrong answers were seven stator winding, four bowed rotor and one rotor misalignment. Nearest Welch distance alone labels 2 of 16 correctly, 3 of 16 using only bins above 2 kHz, so profile-2 recordings lie nearer other classes' profile-1 references. The [family analysis](DSP_FAMILY_SEPARATION.md) finds Ottawa classes overlapping across profiles in every tested representation. References for each operating profile and load come next.

## Inspect Six Recorded Decisions

Each link opens the audio, all eight figures and the recorded explanation; the evidence column links the exact parsed decision and model input in this repository.

| Decision | Outcome | Evidence | What it shows |
| --- | --- | --- | --- |
| [Jin T01, reserved](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-reserved-T01) | Correct, excess Hall adhesive | [decision](../examples/audio-comparison/responses/jin-distances-reserved-T01.json), [input](../examples/audio-comparison/inputs/jin-distances-reserved-T01.json) | Clear separation transfers from front to right microphone |
| [Jin T01, class excluded](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-excluded-T01) | Correct `different` | [decision](../examples/audio-comparison/responses/jin-distances-excluded-T01.json), [input](../examples/audio-comparison/inputs/jin-distances-excluded-T01.json) | The same window is set aside when its reference is withheld |
| [Jin T07, reserved](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-reserved-T07) | Set aside, magnet fracture | [decision](../examples/audio-comparison/responses/jin-distances-reserved-T07.json), [input](../examples/audio-comparison/inputs/jin-distances-reserved-T07.json) | Close magnet-fracture and tight-bearing references |
| [Jin T04, class excluded](https://faustinopalma.github.io/ModelMetis/audio-comparison/#jin-distances-excluded-T04) | Wrong acceptance, tight bearing | [decision](../examples/audio-comparison/responses/jin-distances-excluded-T04.json), [input](../examples/audio-comparison/inputs/jin-distances-excluded-T04.json) | The explanation drifts from a large distance |
| [Ottawa D01](https://faustinopalma.github.io/ModelMetis/audio-comparison/#ottawa-reports-development-D01) | Correct, healthy | [decision](../examples/audio-comparison/responses/ottawa-reports-development-D01.json), [input](../examples/audio-comparison/inputs/ottawa-reports-development-D01.json) | Recognition across operating profiles |
| [Ottawa D03](https://faustinopalma.github.io/ModelMetis/audio-comparison/#ottawa-reports-development-D03) | Wrong, stator winding for rotor unbalance | [decision](../examples/audio-comparison/responses/ottawa-reports-development-D03.json), [input](../examples/audio-comparison/inputs/ottawa-reports-development-D03.json) | A profile-2 recording needs a profile-2 reference |

## Scope Of The Current Evidence

- **Data.** Both public datasets were studied earlier in the project. Fresh recordings and blind listening comparisons are the next validation steps.
- **Machines.** The 12 reserved Jin windows come from four acquisitions, three windows each, and original healthy and fault files use PCM16 and FLOAT encodings respectively. Ottawa motors recur across profiles, so motor identity and class can coincide.
- **New faults.** Excluded-class tests withhold a known reference; genuinely new fault mechanisms are a separate future test.
- **Model and numbers.** Forced nearest distance labels the reserved Jin windows as well as the model. The model adds cited, inspectable explanations and the option to send a case to review; the next comparisons measure its contribution to accuracy.
- **Published scores.** External scores in [benchmark status](DSP_BENCHMARK_STATUS.md) use their own sensors, splits and label budgets and serve as context.
- **Software versions.** The runner and validator kept evolving during the study. [Registered code](../registered/simple-method/README.md) holds the recovered recorded versions; for the one similarity-module version used by configuration A that was not recovered, the exact requests and responses serve as the record.

## Other Directions Explored

Later studies changed the input or the reference representation. Each uses its own inputs and counts, and together they point the current work toward representative references; the [archive page](https://faustinopalma.github.io/ModelMetis/archive/) publishes their selected evidence.

| Variant | Measured observation | Owner |
| --- | --- | --- |
| All 26 diagrams, adding 19 analyses | 6/12 correct, 4/12 wrong, 2/12 false rejections; 4/12 correct and 8/12 wrong excluded-class answers | [All-diagram results](DSP_EXTENSIONS.md) |
| Explicit review of every diagram | 8 paired decisions stay 5/8 correct; wrong assignments fall from 2/8 to 0/8 while false rejections rise from 1/4 to 3/4 | [Attribution audit](DSP_DIAGRAM_AUDIT.md) |
| Removing three diagram types | Primary cases move from 5/8 to 6/8 correct; an identical repeated request returns the wrong class C06 | [Pruning results](DSP_PRUNING_RESULTS.md) |
| Aggregated class cards with adaptive memory, 72 Ottawa acquisitions | Fixed: 16 correct, 11 wrong, 45 review. Adaptive: 18 correct, 41 wrong, 13 review | [Class-memory results](DSP_MEMORY_RESULTS.md) |
| Family separation without a model | Full spectra and cepstrum group 12/12 Jin acquisitions; Ottawa's best whole-profile result is 9/24 | [Family separation](DSP_FAMILY_SEPARATION.md) |

Earlier encoder, teacher/specialist and cross-drone studies remain in the [experiment archive](EXPERIMENTS.md). [Publication policy](PUBLICATION.md) defines what is released.
