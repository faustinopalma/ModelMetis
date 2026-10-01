# Compare DSP Reports With Known References, Then Recognize Or Abstain

**A multimodal model receives the signal-processing report of an unknown recording, one report for each known condition and instructions to name the matching condition or answer `different`.** The method depends on the reference set: each reference must represent its condition as it will actually be recorded. Measured outcomes belong to [Results](RESULTS.md); recorded inputs and decisions can be inspected in the [public comparison](../examples/audio-comparison/README.md).

## The Model Receives Diagrams And Measurements, Not Audio

Every recording is reduced to a deterministic DSP report before any model call. **DSP** means digital signal processing: fixed numerical analyses of the sampled waveform. Each ten-second report contains eight figures and their numerical measurements.

| Figure | What it shows |
| --- | --- |
| Complete recording and waveform | Level, peaks and stability over time |
| FFT amplitude spectrum | Discrete tones and harmonics over the whole interval |
| Welch power spectrum | Averaged spectral shape |
| Spectrogram | How the spectrum changes over time |
| Band power | Energy fractions in fixed frequency bands |
| Envelope and modulation spectrum | Slow amplitude modulation and repeated impacts |
| Autocorrelation | Repeating waveform periods |

The measurements include levels, crest factor, kurtosis, zero-crossing rate, strongest FFT peaks, band power, spectral centroid and flatness, envelope modulation peaks and autocorrelation lags. Their definitions and limits are in the [DSP pipeline](DSP_PIPELINE.md). Because the service accepts at most 50 images, each report's eight figures travel as one contact sheet of 600-by-350-pixel cells; all measurements are sent as text.

One request contains:

1. **Reference reports.** One report per known condition, identified as `C01`, `C02` and so on, with the publisher's class name.
2. **The unknown report.** Identified only as `Q01`; its label, source filename and acquisition details are withheld.
3. **Instructions.** Compare the unknown with every reference across spectral shape, harmonic structure, absolute frequencies, band power, envelope, periodicity and time evolution. Cite measurement or figure identifiers from both reports. Choose the best-supported similar condition, or answer `different` only when every reference is substantially different.

The audio is not sent. It is published so a person can listen to an unknown recording beside each reference and judge the same decision.

## Three Recorded Configurations Change Only The Numerical Guidance

| Configuration | Added to the reports and instructions | Status |
| --- | --- | --- |
| A, reports only | Nothing | Tested on Jin development and Ottawa development |
| B, reports plus distances | A table of Welch spectral distances from the unknown to every reference and between references, with guidance that a much smaller query distance supports a match | Selected on Jin development, then run on reserved Jin windows |
| C, calibrated rule | Per-class distance thresholds: accept the nearest reference only within its threshold | Exploratory replay designed after inspecting configuration B |

The Welch distance is the root-mean-square difference, in decibels, between two Welch power spectra after each is converted to decibels and centered on its mean. Centering removes a constant gain difference; microphone frequency response, position and operating regime still change the shape. Configuration C's thresholds were the largest observed development distance per class times 1.2, fitted on eight additional labeled windows. A forced nearest-distance rule is also recorded as a numerical control, so the model's contribution can be compared with numbers alone.

## The Answer Must Be Traceable

The response contains one comparison per reference, with short similarities, differences and evidence identifiers, then either `similar` with one condition or `different` with none. A validator rejects missing comparisons, invented identifiers and answers that do not cite both the reference and the unknown. These checks prove that the answer is well formed and grounded in supplied evidence; they do not prove the answer is correct. Correctness is scored only against publisher labels.

## Abstention Sends The Case To A Person

`different` means none of the supplied references is similar enough. It is an abstention, not a newly discovered fault. Its meaning depends on the test:

| Test | Correct reference supplied? | Correct answer | Wrong answers |
| --- | --- | --- | --- |
| Recognition | Yes | That condition | Another condition (unsafe); `different` (false rejection) |
| Excluded-class test | No, it is deliberately removed | `different` | Any condition (unsafe acceptance) |

A false rejection costs human time but is caught. A wrong condition is the dangerous error, because a workflow that reviews only abstentions would accept it. Excluded-class tests show whether the model can reject when its class is missing; they do not test genuinely new fault mechanisms.

## Representative References Are A Condition Of The Method

The model can only recognize what the references show. Choose them by these rules:

1. **Match the operating conditions.** A reference should share the microphone position, acquisition chain, speed and load of the recordings it must recognize. A reference from another regime tests transfer, not recognition.
2. **Select before testing.** Fix references by a written rule that uses no test outcomes. Keep whole acquisitions on one side: never place windows of one recording in both references and tests, and treat windows of one recording as dependent.
3. **Represent every family separately.** When two recordings with the same label behave very differently, the label covers more than one acoustic family, subtype or operating regime. Supply each as its own reference instead of averaging them. The difference alone does not prove two distinct physical faults; speed, load, mounting or microphone can cause it.
4. **Check that references are distinguishable.** If two references of different classes are closer to each other than the unknowns are to their own reference, expect missed recognitions and wrong acceptances between those classes.

The recorded experiments used one reference per class. Jin references are the first ten seconds of each class's front-microphone recording; Ottawa references are the profile-1 unloaded acquisition of each class. Both rules were fixed before testing. Jin's front references transferred to right-microphone recordings; Ottawa's profile-1 references did not represent profile 2.

## The Method Fails In Recognizable Ways

| Failure | Recorded sign |
| --- | --- |
| References miss the operating regime | Ottawa profile 2 lay closer to other classes' profile-1 references; most decisions were confident wrong classes |
| Two references lie close together | Jin magnet fracture and tight bearing were 3.04 dB apart; magnet fracture was missed or confused with tight bearing |
| The model argues past the numbers | An excluded healthy window was accepted as tight bearing at 6.35 dB, while another excluded window at 3.92 dB was rejected |
| A threshold moves the error | Calibrated thresholds rejected every excluded window and every magnet-fracture window |
| The representation hides the difference | No tested Ottawa representation separated classes across profiles in the [family analysis](DSP_FAMILY_SEPARATION.md) |

Later variants tried to fix these failures by removing diagram types, adding 19 extra analyses or aggregating references into adaptive class memory. They did not improve safety and remain [archived limits](RESULTS.md#later-variants-are-archived-limits).

## Technical Contract

The [whole-report comparison contract](DSP_REPORT_COMPARISON.md) defines request folders, identifiers, admission limits and the one-attempt rule. The [labeled-results record](DSP_LABELED_RESULTS.md) documents dataset selection, calibration and every technical attempt. [Reproduction commands](../scripts/README.md) separate offline verification from new paid inference.
