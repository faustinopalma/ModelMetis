# Compare DSP Reports With Known References, Then Recognize Or Send To Review

**The system receives an audio recording, turns it into a signal-processing report, and gives a general multimodal model that report together with one report for each known condition and instructions to name the matching condition or answer `different`.** The reference set drives the result: each reference represents its condition as it will actually be recorded. Measured outcomes belong to [Results](RESULTS.md); recorded inputs and decisions can be inspected in the [public comparison](../examples/audio-comparison/README.md).

## The System Turns Each Recording Into Diagrams And Measurements

The system analyzes every recording into a deterministic DSP report before the model call. **DSP** means digital signal processing: fixed numerical analyses of the sampled waveform. Each ten-second report contains eight figures and their numerical measurements.

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
2. **The unknown report.** Identified as `Q01`; its label, source filename and acquisition details stay with the evaluator.
3. **Instructions.** Compare the unknown with every reference across spectral shape, harmonic structure, absolute frequencies, band power, envelope, periodicity and time evolution. Cite measurement or figure identifiers from both reports. Choose the best-supported similar condition, and answer `different` when every reference is substantially different.

The original audio is published beside the reports, so a person can listen to an unknown recording and each reference and judge the same decision.

## Three Recorded Configurations Change Only The Numerical Guidance

| Configuration | Added to the reports and instructions | Status |
| --- | --- | --- |
| A, reports only | Reports and instructions as described above | Tested on Jin development and Ottawa development |
| B, reports plus distances | A table of Welch spectral distances from the unknown to every reference and between references, with guidance that a much smaller query distance supports a match | Selected on Jin development, then run on reserved Jin windows |
| C, calibrated rule | Per-class distance thresholds: accept the nearest reference only within its threshold | Exploratory replay designed after inspecting configuration B |

The Welch distance is the root-mean-square difference, in decibels, between two Welch power spectra after each is converted to decibels and centered on its mean. Centering removes a constant gain difference; microphone frequency response, position and operating regime still change the shape. Configuration C's thresholds were the largest observed development distance per class times 1.2, fitted on eight additional labeled windows. A forced nearest-distance rule is also recorded as a numerical control, so the model's contribution can be compared with numbers alone.

## The Answer Must Be Traceable

The response contains one comparison per reference, with short similarities, differences and evidence identifiers, then either `similar` with one condition or `different` with none. A validator checks that every reference is compared and that each comparison cites real identifiers from both the reference and the unknown. This makes every answer traceable to supplied evidence; correctness is scored separately against publisher labels.

## `different` Sends The Case To A Person

`different` means none of the supplied references is similar enough, so the case goes to human review. Its meaning depends on the test:

| Test | Correct reference supplied? | Correct answer | Wrong answers |
| --- | --- | --- | --- |
| Recognition | Yes | That condition | Another condition (unsafe); `different` (false rejection) |
| Excluded-class test | Withheld on purpose | `different` | Any condition (unsafe acceptance) |

A false rejection costs human time and reaches a person. A wrong condition is the error to drive toward zero, because a workflow that reviews `different` answers would accept it. Excluded-class tests measure how well the model sets aside a case whose condition has no reference; genuinely new fault mechanisms are a separate future test.

## Representative References Drive Good Decisions

The model recognizes the conditions that the references show. Choose them by these rules:

1. **Match the operating conditions.** A reference shares the microphone position, acquisition chain, speed and load of the recordings it should recognize. A reference from another regime measures transfer between regimes.
2. **Select before testing.** Fix references by a written rule that uses no test outcomes. Keep each acquisition on one side, with all its windows either among references or among tests, and treat windows of one recording as dependent.
3. **Represent every family separately.** When two recordings with the same label behave very differently, the label covers more than one acoustic family, subtype or operating regime, and each gets its own reference. The cause can be speed, load, mounting or microphone as well as the fault itself.
4. **Check that references are distinguishable.** When two references of different classes lie closer to each other than the unknowns lie to their own reference, those classes need additional or more specific references.

The recorded experiments used one reference per class. Jin references are the first ten seconds of each class's front-microphone recording; Ottawa references are the profile-1 unloaded acquisition of each class. Both rules were fixed before testing. Jin's front references carried over to right-microphone recordings; Ottawa's profile-1 references now need companions from profile 2 and the other profiles.

## Recorded Error Patterns Guide The Next Improvements

| Pattern | Recorded sign | Next improvement |
| --- | --- | --- |
| References from another operating regime | Ottawa profile 2 lay closer to other classes' profile-1 references | References for every profile and load |
| Two references close together | Jin magnet fracture and tight bearing were 3.04 dB apart | A magnet-fracture reference for its other microphone regime |
| Explanations that drift from the numbers | An excluded healthy window was accepted as tight bearing at 6.35 dB, while another excluded window at 3.92 dB was set aside | Instructions and checks that keep the explanation consistent with the distances |
| A threshold that shifts errors toward review | Calibrated thresholds set aside every excluded window and every magnet-fracture window | Thresholds calibrated on regime-matched references |
| Overlapping representations | Ottawa classes overlap across profiles in every representation of the [family analysis](DSP_FAMILY_SEPARATION.md) | Regime-matched references and new comparison features |

We also explored removing diagram types, adding 19 extra analyses and aggregating references into adaptive class memory; [Results](RESULTS.md#other-directions-explored) summarizes what each showed.

## Technical Contract

The [whole-report comparison contract](DSP_REPORT_COMPARISON.md) defines request folders, identifiers, admission limits and the one-attempt rule. The [labeled-results record](DSP_LABELED_RESULTS.md) documents dataset selection, calibration and every technical attempt. [Reproduction commands](../scripts/README.md) separate offline verification from paid inference.
