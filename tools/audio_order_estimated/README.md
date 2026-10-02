# Normalize Audio To An Estimated Acoustic Base

This tool estimates a time-varying acoustic base frequency from multiple harmonic peaks, then produces the same angular-domain report as the supplied-RPM tool. It returns an explicit unavailable result when the recording lacks sufficiently strong, unambiguous harmonic evidence. An accepted acoustic base does not identify shaft RPM: blade passage, electrical excitation, combustion events and gears can produce different periodicities.

All files and generated runs stay in this new folder and its sibling [known-speed tool](../audio_order_known/README.md). The shared engine and renderer live in that sibling, so keep both folders together. Dependencies are NumPy, SciPy, soundfile and Matplotlib; the tools do not use the existing application, a cloud API or an AI model.

## Run Without Supplying RPM

Use the dedicated environment described in the sibling README and run from the repository root:

```powershell
tools/audio_order_known/.venv/Scripts/python.exe -B -m tools.audio_order_estimated.cli recording.wav --output tools/audio_order_estimated/runs/motor-auto
tools/audio_order_known/.venv/Scripts/python.exe -B -m tools.audio_order_estimated.cli recording.wav --min-hz 15 --max-hz 150 --frame-seconds 0.5 --hop-seconds 0.1 --start 2 --duration 6 --channel 1 --output tools/audio_order_estimated/runs/motor-bounded
```

No speed or expected fundamental is supplied. The default search interval is 10-300 Hz; these bounds are assumptions that constrain possible acoustic periodicities and are recorded in the report. The default frame is 0.5 seconds with a 0.1-second hop. A frame must span at least four periods at the lower bound, so searching down to 5 Hz requires at least `--frame-seconds 0.8`. The hop must not exceed half a frame. There is a 2,000-frame limit.

`--start`, `--duration`, `--channel`, `--max-order`, `--cycles-per-frame` and `--samples-per-cycle` have the same meaning as in the known-speed tool. Outputs require a new directory; existing reports are never overwritten.

Exit code `0` means a normalized report was generated; `3` means the original report and estimation evidence were generated but normalization was unavailable; `2` means invalid input or an I/O failure. Automation should inspect both the exit code and `normalization.status` in `measurements.json`.

## Harmonic Agreement And Continuity Determine Acceptance

Each Hann-windowed frame is analyzed with a SciPy periodogram. Fourfold FFT zero-padding improves peak interpolation without increasing physical spectral resolution. Peaks must exceed 8 dB prominence, approximately 12 dB above the median spectral floor and -30 dB relative to the strongest power peak. Up to 40 peaks propose base candidates through integer harmonic division, using at most eight harmonics by default.

Candidates need at least two distinct matched harmonic orders with greatest common divisor one. This rejects unsupported subharmonic interpretations, while allowing a missing fundamental when, for example, orders 2 and 3 are present. A weighted fit refines each base, and a score measures matched peak-amplitude coverage and frequency agreement. These scores are heuristics, not calibrated confidence probabilities.

Dynamic programming selects a path through up to 12 competing candidates per frame with a penalty on logarithmic frequency jumps. Every frame must have score at least 0.65 and separation from its strongest alternative of at least 0.08. Changes above 20% between adjacent selected frames are rejected. Missing or unreliable frames stop whole-interval normalization; the tool never silently bridges gaps. Select a shorter coherent interval when appropriate.

The accepted trace is linearly interpolated only between complete-frame centers. Unsupported leading/trailing half-frames are excluded rather than extrapolated, and the angular engine subsequently applies its own filter-edge and complete-cycle exclusions. The normalized report names its horizontal coordinate **acoustic relative order** and stores `shaft_rpm: null`.

## Interpret Ambiguity Before Comparing Machines

Silence, broadband noise, a single isolated tone, competing periodic sources, missing harmonics, fast acceleration and resonance-dominated spectra can prevent acceptance or lead to an incorrect acoustic family. Two even shaft harmonics can support an acoustic base twice the shaft frequency; the audio alone does not resolve that physical relationship. A stable accepted reference can also come from electrical hum or another machine.

The report preserves the original waveform, frequency spectrum and spectrogram alongside the candidate trace and normalized views. `measurements.json` retains each frame's candidates, score, margin, matched harmonic orders and acceptance status. `arrays.npz` stores the accepted base and its exact time support. This evidence allows inspection of harmonic selection before comparing reports; the thresholds have not been calibrated for industrial recordings.

The synthetic demo and tests exercise missing fundamentals, dominant overtones and moderate run-up. They establish numerical implementation behavior, not accuracy on real engines or a diagnostic improvement. The shared demo command is documented in the sibling README; its generated examples remain local and ignored by Git.

## Tacholess Tracking And Pitch Estimation Are Established Techniques

- [MathWorks: rpmtrack](https://www.mathworks.com/help/signal/ref/rpmtrack.html) estimates speed from time-frequency ridges when the ridge's physical order and guiding points are supplied. It documents coarse ridge extraction followed by Vold-Kalman refinement, citing Urbanek, Barszcz and Antoni, *A Two-Step Procedure for Estimation of Instantaneous Rotational Speed with Large Fluctuations*, Mechanical Systems and Signal Processing 38, 96-102. This tool instead estimates an acoustic harmonic family without asserting its physical order; it does not implement the Vold-Kalman method.
- [librosa: probabilistic YIN](https://librosa.org/doc/0.11.0/generated/librosa.pyin.html) documents fundamental-frequency candidates, probabilistic voicing and Viterbi sequence decoding, citing Mauch and Dixon's pYIN and de Cheveigne and Kawahara's YIN. It is an established alternative for speech/music periodicity; it is not used here and its published accuracy does not transfer to this harmonic estimator.
- [MathWorks: order analysis](https://www.mathworks.com/help/signal/ug/order-analysis-of-a-vibration-signal.html) explains the constant-phase resampling step used after selecting a reference frequency.

The implementation uses proven SciPy spectral analysis, peak detection, filtering and Hilbert transforms. The harmonic candidate scoring, greatest-common-divisor check and acceptance thresholds are the local, explicitly tested engineering choices. No claim of reproducing a published tacholess algorithm or of measuring shaft speed is made.
