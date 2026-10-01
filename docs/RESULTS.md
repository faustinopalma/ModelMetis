# Current Evidence Does Not Support Autonomous Diagnosis

**Keep the numerical baseline and do not promote the tested triple-pruning candidate.** Spectral representations separate the observed Jin classes, but Ottawa remains difficult across operating conditions. The latest pruning experiment improves one healthy example while an identical-request repeat introduces an unacceptable wrong assignment. No final clean evaluation, independent human benchmark or operational promotion has occurred.

The [interactive evidence explorer](https://faustinopalma.github.io/ModelMetis/) and [local snapshot](../examples/README.md) expose the observations behind this conclusion. These studies answer different questions and must not be pooled into a single accuracy score.

## The Studies Answer Different Questions

| Question | Measured observation | Interpretation and detailed owner |
| --- | --- | --- |
| Can the full DSP report support recognition and rejection? | All-diagram campaign: 6/12 correct known recognitions, 4/12 wrong known assignments, 2/12 false rejections; 4/12 correct excluded rejections and 8/12 wrong acceptances | Incorrect assignments dominate the fourteen errors. [All-diagram results](DSP_EXTENSIONS.md) |
| Does explicit diagram review change error direction? | Eight paired decisions stay 5/8 correct; wrong assignments fall from 2/8 to 0/8 while known-class false rejections rise from 1/4 to 3/4 | More caution, not better recognition. [Attribution audit](DSP_DIAGRAM_AUDIT.md) |
| Which representations distinguish families across regimes? | Full spectra and cepstrum reach 12/12 Jin acquisition groups across withheld directions; Ottawa's best whole-profile result is 9/24, with overlap for every class | Grouped forced-label checks on consumed data. [Family separation](DSP_FAMILY_SEPARATION.md) |
| Does removing error-associated evidence help? | Eight primary cases improve from 5/8 to 6/8 with triple removal, but identical D03 requests give Other and wrong C06 | The candidate fails the observed safety gate. [Crossed pruning results](DSP_PRUNING_RESULTS.md) |

Other means the structured no-match response, not a discovered fault category. With a known class present it is a false rejection; with that class withheld it is correct. An accepted wrong label would not trigger a rejection-only human-review loop. These outcome meanings determine the safety comparison.

## Inspect Three Complementary Examples

| Public example | Evidence to inspect | What it establishes |
| --- | --- | --- |
| Ottawa D03, unsafe repeat | Correct rotor-unbalance reference versus chosen bowed-rotor reference; decision and counterevidence | The model can acknowledge conflicts and still assign a wrong class |
| Ottawa D01, healthy | Healthy query/reference pair and the triple-removal decision; full-control outcome in the crossed matrix | One observed recovery after combined removal, not an isolated single-view effect |
| Jin T01, known and excluded | Correct reference when present, then Other when it is withheld | Recognition and rejection can both work for this recording |

The comparison retains all eight primary candidate decisions and both repeats. The [complete 46-outcome matrix](../examples/results/pruning-decisions.json) includes controls, single/combined removals, targeted kurtosis removal and repeats. The model received 23 retained diagram types; four are displayed for rapid inspection. Source text inputs and selected parsed decisions are published with hashes tying them to the retained local originals.

## Reconcile Attribution With Measured Separation

The model frequently cites band power and dominant-frequency tracking. In Ottawa their median within-family/nearest-family distance ratios are 3.67 and 4.17, so changes within one label can exceed differences between labels. That makes them candidates for controlled removal, not automatic deletion. Retained FFT/STFT views can carry similar information, and deleting rejection cues can sometimes expose a wrong nearest-class assignment.

![Grouped Jin separation](../examples/results/jin-summary.png)

![Grouped Ottawa separation](../examples/results/ottawa-summary.png)

The [structured separation results](../examples/results/family-separation.json) and [family-specific matrices](DSP_FAMILY_SEPARATION.md) retain denominators and exceptions. A successful ranking does not establish a calibrated acceptance radius. A failed representation does not show that no method could classify the underlying audio.

## What Remains Unmeasured

Independent-machine generalization, genuinely unseen faults, a clean final comparison after policy selection, expert accuracy under matched information and causal fidelity of model explanations remain unestablished. [Benchmark status](DSP_BENCHMARK_STATUS.md) explains why published results from other tasks and plausible human difficulty do not establish state-of-the-art performance here. Earlier model-family and teacher/specialist studies remain in [the archive](EXPERIMENTS.md); [publication policy](PUBLICATION.md) defines the curated release boundary.
