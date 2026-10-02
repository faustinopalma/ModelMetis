# The Method Recognizes Conditions In Matched Regimes, And Speed Normalization Carries It Across Speeds

**With DSP reports plus Welch distances, the model recognized 11 of 12 reserved Jin windows and correctly set aside 2 of 4 cases whose condition had no reference. On the MAFAULDA rig, whose references run at 1.0-2.0 times the test speed, speed-normalized reports recognized 40 of 72 cases against 27 of 72 before normalization.** With reports only, the model recognized 4 of 16 Ottawa profile-2 acquisitions recorded at twice the reference drive frequency. An exploratory calibrated replay on the same Jin inputs shifted the balance toward review: 9 of 12 recognized and 4 of 4 set aside. Each configuration keeps its own counts. Nearest Welch distance alone also labels all 12 reserved Jin windows, so the next comparisons measure what the model adds beyond these numbers. Production benches fix speed and load in advance, which places every test in the matched-regime condition.

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

## Ottawa Recordings Follow Speed And Load More Closely Than Fault

On Ottawa the model always named a class. It recognized both healthy acquisitions, one stator-winding and one bowed-rotor acquisition; its twelve wrong answers were seven stator winding, four bowed rotor and one rotor misalignment. Four measured properties of the recordings explain this result. Read beside its references, each query supports the model's choice about as well as its labeled class.

1. **References and queries run at different speeds.** The publisher defines each profile by drive frequency: profiles 1-4 hold 15, 30, 45 and 60 Hz, and profiles 5-8 ramp between those values. References come from profile 1 at 15 Hz and queries from profile 2 at 30 Hz, so every rotation-locked line in a query sits near twice the frequency of the matching reference line.
2. **Each query lies almost equally close to all eight references.** For every query, the eight Welch distances span 1.14-2.71 dB and the nearest reference leads the second by 0.00-0.36 dB. Nearest distance names bowed rotor for 14 of 16 queries and labels 2 of 16 correctly, 3 of 16 using only bins above 2 kHz. In the Jin table above, three of four classes lead the next reference by 1.6 dB or more.
3. **Load alone also mixes the classes.** At the same 30 Hz speed, the nearest acquisition recorded at the other load belongs to the same class in 7 of 16 cases with the same Welch distance, and in 4 or 5 of 16 with cepstrum, relative-floor Welch or STFT quantiles. In these microphone recordings, each fault's signature is small compared with the change between operating states.
4. **Each condition is one motor.** The publisher describes eight motors with artificially induced faults and supplies one acquisition per condition, profile and load. Every class therefore rests on a single unit, and motor identity travels with the condition.

The published scores verified for this dataset combine accelerometers with the microphone ([Selective Embedding preprint](https://arxiv.org/abs/2507.13399), Table 3). Two directions follow from these measurements: references recorded at each speed and load, and representations that subtract the healthy recording of the same regime, defined in the [difference protocol](DIFFERENCE_PROTOCOL.md). The [family analysis](DSP_FAMILY_SEPARATION.md) extends the comparison to 24 representations. Recompute items 2 and 3 from the published [family-separation record](../examples/archive/results/family-separation.json):

```powershell
python -m scripts.ottawa_geometry
```

## Speed Normalization Carries Recognition Across Speed Changes

MAFAULDA records one rig in 10 conditions (normal, imbalance, two misalignments and three bearing defects in two positions) at many shaft speeds, with a tachometer. Its 72 model cases, fixed with a seed before any call, pair each fault query with one reference per condition recorded at 1.0, 1.1, 1.3 or 2.0 times the query's speed. Guessing scores about 1 in 10.

| Configuration | x1.0 | x1.1 | x1.3 | x2.0 | All |
| --- | --- | --- | --- | --- | --- |
| Reports only | 10/18 | 9/18 | 6/18 | 2/18 | 27/72 |
| Reports plus stated speed and an order figure | 9/18 | 14/18 | 8/18 | 2/18 | 33/72 |
| Speed-normalized reports, measured speed | **13/18** | 10/18 | **9/18** | **8/18** | **40/72** |
| Speed-normalized reports, base estimated from audio | 12/18 | 10/18 | 5/18 | 4/18 | 31/72 |

Speed-normalized reports come from the [known-speed tool](../tools/audio_order_known/README.md): every reference and query is resampled to its own shaft rotation, so rotation-locked tones share one order axis, and the hertz figures stay beside the order figures. Against reports only, the paired gains and losses are +20/-7 (p = 0.02). Without a model, the nearest order spectrum up to the 100th order recognizes 213/343 queries at x1.1 and 73/160 at x2, against 78/343 and 21/160 for the hertz spectrum; at equal speed the hertz spectrum separates 246/387 by itself. The [speed study](DIFFERENCE_SCREEN.md) records every arm, the numerical checks on UORED, Ottawa and FSTF, and the estimator calibration; the [published record](../examples/results/speed-normalization-summary.json) keeps the aggregate counts.

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

- **Data.** Jin and Ottawa were studied earlier in the project; the six MAFAULDA arms were designed in sequence on the same 72 cases. Fresh recordings, a bench pilot and blind listening comparisons are the next validation steps.
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
