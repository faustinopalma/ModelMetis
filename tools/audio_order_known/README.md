# Normalize Audio To Supplied Shaft Speed

This tool produces an offline audio report in shaft orders using a supplied constant RPM or a time-varying RPM trace. Angular resampling makes speed-proportional tones comparable across speeds; it preserves recorded gain, so load, resonances and speed-dependent amplitude remain visible.

The implementation, tests and generated files stay inside the two new sibling folders `tools/audio_order_known` and `tools/audio_order_estimated`. Neither tool imports the existing `src/modelmetis` code, calls a model, changes cloud resources or modifies shared configuration. The estimated-base tool reuses this folder's numerical engine and report renderer; keep both folders together.

## Run With Constant Or Time-Varying RPM

Run these commands from the repository root using Python 3.12 or newer. A dedicated environment keeps dependency installation separate from other work; an existing interpreter with the four declared dependencies can also run the tools without installation.

```powershell
python -m venv tools/audio_order_known/.venv
tools/audio_order_known/.venv/Scripts/python.exe -m pip install -r tools/audio_order_known/requirements.txt
tools/audio_order_known/.venv/Scripts/python.exe -B -m tools.audio_order_known.cli recording.wav --rpm 1800 --output tools/audio_order_known/runs/motor-1800
tools/audio_order_known/.venv/Scripts/python.exe -B -m tools.audio_order_known.cli recording.wav --rpm-trace speed.csv --start 2 --duration 6 --channel 1 --output tools/audio_order_known/runs/motor-runup
```

The speed trace must contain exactly these two columns, strictly increasing times and finite positive RPM. Times are measured from the original recording's beginning, including when `--start` selects a later interval. The trace must cover every selected sample; interpolation is linear and extrapolation is rejected.

```csv
time_seconds,rpm
0,1800
5,2100
10,2400
```

`--rpm` assumes constant speed throughout the selected interval. The default selection is the first 10 seconds, capped by the available recording; the report records both requested and actual duration. `--channel` is 1-based and defaults to the first native channel, with no channel averaging. WAV, FLAC and other formats supported by the installed libsndfile are accepted. Limits are 120 selected seconds, 256 MiB source bytes and 40 million decoded channel samples.

## Read The Report And Its Numerical Evidence

Open `report.html` directly in a browser. Its figures and audio are embedded, and no server or network is required. Keep the output folder together to use its adjacent numerical downloads.

- `report.html`: waveform and levels, original FFT/Welch, original spectrogram, RPM reference, normalized FFT/Welch, time-order map, angular envelope spectrum, cycle average and angular autocorrelation.
- `measurements.json`: input hash, exact selection/channel, DSP parameters, runtime versions, implementation hashes, peak orders and reference provenance.
- `arrays.npz`: full original spectra, angular waveform/time coordinates and normalized numerical curves/maps. Load with `numpy.load(..., allow_pickle=False)`.
- `images/`: individual PNG figures; `manifest.json` binds all report artifacts by SHA-256.

Every invocation requires a new output directory and refuses to overwrite existing results. Generated runs, environments and validation files are ignored by Git. Reports can contain recording names and sensitive acoustic data; keep them local unless explicitly reviewed for publication.

## Angular Resampling Aligns Speed-Proportional Components

For constant shaft frequency `f_rot = RPM / 60`, order is `frequency / f_rot`. For changing speed, the tool integrates `f_rot(t)` with the trapezoidal rule, filters the original waveform and interpolates it onto uniformly spaced reference-cycle positions. It then computes FFT, Hann-windowed Welch PSD and spectrograms in the angular domain, rather than merely relabeling a frequency axis.

The default is 512 samples per cycle and eight cycles per spectral frame, giving 0.125-order bin spacing when eight complete cycles are available. Options `--samples-per-cycle`, `--cycles-per-frame` and `--max-order` control the grid, resolution and displayed bandwidth. At least four complete interior cycles are required. The renderer uses explicit cell edges for single-frame maps.

An eighth-order forward-backward Butterworth low-pass precedes resampling. Its cutoff is the smaller of `0.45 * sample_rate` and `0.4 * samples_per_cycle * minimum_base_hz`. The maximum admitted order is `0.8 * cutoff / maximum_base_hz`; requests exceeding this conservative bandwidth are rejected. The first and last 50 ms and incomplete cycles are excluded. The filter and linear interpolation have amplitude and edge effects; extreme acceleration can require more specialized tracking and filtering.

Angular density is expressed in `FS^2/order`, while original density is `FS^2/Hz`. For constant speed the corresponding density transformation is `P_order(order) = f_rot * P_Hz(order * f_rot)`; an axis-only substitution would miss this factor. Integration of each density recovers its corresponding power. Changing-speed angular averages weight each cycle equally, giving faster time intervals more samples.

The phase origin is arbitrary rather than tachometer-triggered. Cycle averaging can suppress asynchronous impacts, and the envelope is calculated over the full retained angular band rather than a tuned bearing-resonance band. Playback uses the selected original audio converted to PCM16; full-scale overflow is reported and clipped only for playback. No amplitude normalization or fault classification is performed.

## Reproduce The Synthetic Checks

```powershell
tools/audio_order_known/.venv/Scripts/python.exe -m pip install "pytest>=8.3,<9" "ruff>=0.11,<1"
tools/audio_order_known/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider -o pythonpath=. tools/audio_order_known tools/audio_order_estimated
tools/audio_order_known/.venv/Scripts/python.exe -B -m ruff check --no-cache tools/audio_order_known tools/audio_order_estimated
tools/audio_order_known/.venv/Scripts/python.exe -B -m tools.audio_order_known.demo --name demo-v1
```

The demo synthesizes a six-second 30-to-42 Hz run-up with orders 1, 2, 3 and 5, strongest at order 2, plus seeded Gaussian noise. It produces `runs/demo-v1/report.html` in each tool folder and a shared validation summary in this folder's `runs/demo-v1-inputs/validation.json`. The check requires the dominant order to remain 2 for both tools and the automatic base-frequency error to stay below 2.5% at every normalized sample. Use another `--name` to preserve earlier runs.

The tests also cover constant/changing speed, integrated power, invalid RPM, missing fundamentals, stronger overtones, noise, silence, signal gaps, anti-alias rejection, native-channel selection, malformed speed traces, report hashes, overwrite protection and single-frame map area. These are implementation checks, not a real-machine diagnostic benchmark.

## Existing Techniques Establish The Method

- [MathWorks: Order Analysis of a Vibration Signal](https://www.mathworks.com/help/signal/ug/order-analysis-of-a-vibration-signal.html) describes constant-phase resampling and why it reduces speed-change smearing.
- [MathWorks: orderspectrum](https://www.mathworks.com/help/signal/ref/orderspectrum.html) documents angular-domain average spectra. Its default flat-top RMS spectrum differs from this implementation's Hann-windowed PSD; numerical outputs are not claimed to reproduce MATLAB.
- [SciPy: resample_poly](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html) documents anti-alias low-pass filtering in fixed-ratio resampling. The variable-speed coordinate transform here uses SciPy filtering and NumPy interpolation instead of fixed-ratio resampling.
- [Estimated-base tool](../audio_order_estimated/README.md) documents the tacholess alternative, supporting sources and ambiguity controls.
