# Deterministic Audio DSP Reports

The DSP pipeline produces numerical measurements, seven analytical views, a self-contained HTML report and JSON/Markdown evidence. It analyzes every interval, including the complete 600-second Jin recording, without model calls or diagnostic labels. EXP-011's separate STFT-only renderer and frozen evidence remain unchanged.

## Generated Examples

The local browser index is `artifacts/dsp-examples-v2/index.html`. Each anonymous report is under its recording ID and can be opened directly without a server. The [example manifest](../configs/dsp-examples-v1.json) fixes the inputs independently of their measured results; the [versioned summary](../ml/dsp-report-examples-v2.json) preserves measured execution times and hashes. Local report artifacts are deliberately not published to Git.

| Dataset | ID | Input | Sampling | Measured intervals | Images | Final report time |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Drone | R0001 | Original, 0.5 s, mono PCM24, A/mic1 | 16,000 Hz | 1 | 8 | 1.597 s |
| Jin motor | R0002 | Complete original 600 s mono FLOAT WAV | 44,100 Hz | 120 | 29 | 177.949 s |
| AI Mechanic | R0003 | Existing 10 s mono PCM16 export | 16,000 Hz | 2 | 15 | 7.885 s |
| Ottawa motor | R0004 | Existing 10 s mono PCM16 development export, already peak-normalized | 42,000 Hz | 2 | 15 | 9.155 s |

Total: four recordings, 620.5 seconds of audio, 125 measured intervals and 67 images. The final suite command took 198.307 seconds including interpreter startup and index generation. These are single local observations, not controlled throughput benchmarks. Numerical arrays dominate storage: the final 212 hash-verified files total 896,639,571 bytes, about 855 MiB. The human-readable report and future interpreter package do not require those large array files.

Examples of actual measurements from the first interval of each report are below. They describe the signal and must not be interpreted as component identity, fundamental rotational frequency or fault evidence. Ottawa's earlier peak normalization and the different acquisition chains prevent a calibrated absolute-level comparison across rows.

| Dataset | RMS, dB re 1 FS | Peak, FS | DC offset, FS | Three strongest reported FFT peaks |
| --- | ---: | ---: | ---: | --- |
| Drone | -10.142 | 0.879239 | -0.064489 | 306.0, 614.0, 252.0 Hz |
| Jin motor | -24.063 | 0.173207 | -0.000028 | 5.4, 7.6, 48.6 Hz |
| AI Mechanic | -15.292 | 0.346130 | -0.004781 | 37.0, 18.6, 0.4 Hz |
| Ottawa motor | -6.674 | 0.949982 | 0.052943 | 43.8, 73.2, 102.4 Hz |

These four files demonstrate format, duration and sampling-rate coverage, not classification performance. Source rights and transformation histories are recorded in the example manifest: Yi, Choi and Lee, Zenodo 7779574 v1, CC BY 4.0; Linjie Jin, Mendeley 9dpmkgpncw v1, CC BY 4.0; Eoin / AI Mechanic, Kaggle v1, Apache-2.0; Mert Sehri and Patrick Dumond, Mendeley msxs4vj48g v2, CC BY 4.0. No protected drone C or Ottawa final-test recording was opened. No additional human labels or physical diagnoses were requested.

## Analysis Contract

**FFT** means **Fast Fourier Transform**, an efficient computation of the discrete Fourier transform. Here it produces a spectrum for the complete analysis interval. **STFT** means **Short-Time Fourier Transform**, a sequence of windowed transforms that retains time variation. **PSD** means **power spectral density**, power per unit frequency. **RMS** means **root mean square**, a measure of effective signal amplitude. These are complementary measurements, not interchangeable pictures of the same quantity.

The [configuration](../configs/dsp-report-v1.json) is serialized and hashed in every run. The [numerical core](../src/modelmetis/dsp.py) uses NumPy and SciPy; the [report renderer](../src/modelmetis/dsp_report.py) uses Matplotlib and Pillow. The native ARM64 environment and [existing dependency pins](../ml/requirements-visual-audio-windows-arm64.txt) are reused. No package was installed or environment merged for this stage; the x64 ML runtime is unchanged.

1. Decode WAV/FLAC by content using the existing integrity-checked decoder, including RIFF/chunk/frame checks, FLAC PCM checksum verification and its checked fallback. File extension does not determine the encoding. Retain source byte/PCM hashes, channel count, sample rate, subtype and declared prior processing in a separate provenance file. For multichannel integrity, the reused validator also computes a mean-channel projection; the actual analysis retains every native channel, including opposite-polarity channels that would cancel under downmixing.
2. Keep the native sample rate and channel signals. Do not apply gain normalization, resampling, silence removal or duration padding. Split the complete recording into nonoverlapping five-second intervals and retain the final partial interval. Sample offsets are native-rate, end-exclusive, and map directly to recording time. Intervals are not asserted to be homogeneous regimes or independent acquisitions.
3. Calculate all numerical measurements for every interval/channel and retain arrays. Create a complete-recording min/max waveform and RMS/peak overview. Detailed plots use a fixed uniform time schedule, including the first and last interval, with at most four illustrated intervals per channel. Jin uses intervals 1, 40, 80 and 120; the other 116 intervals still have measurements and arrays. Unillustrated intervals are not cleared of short events.
4. Preserve original levels for waveform, RMS, peak, clipping and DC offset. Subtract the interval mean only for spectral, autocorrelation and envelope analyses. Record this transformation explicitly. Strictly short intervals with fewer than 32 samples retain level/quality measurements and are marked spectrally unavailable rather than padded into evidence.
5. Write versioned output to a new directory, never overwrite an attempt, and preserve errors in the run manifest. Reports use anonymous recording/channel/interval IDs. Source filenames, dataset diagnoses and answer-bearing path components are excluded from report text and images. Hashes, runtime package versions, exact configuration and operation timings bind the output to its provenance.

The default safety limits are 128 MiB of source bytes, 40 million decoded channel-samples, eight channels and 128 intervals. Exceeding a limit fails explicitly; it does not silently truncate the recording. Adjusting limits or DSP parameters requires an explicit configuration and a fresh output directory. Reports are calculated in memory interval by interval after decoding; this is an offline tool, not a streaming or hard-real-time implementation.

## Views And Measures

| View | Computation and recorded measures | Interpretation limit |
| --- | --- | --- |
| Waveform and levels | Min/max, RMS and peak in contiguous 20 ms level frames; full-recording overview; raw/AC RMS, DC, crest factor, Pearson kurtosis, zero-crossing rate, silence and full-scale clipping | Fixed display axes; exact out-of-range peaks remain in measurements. Level-change candidates at 6 dB are not validated regime boundaries. |
| FFT amplitude | Full-interval real FFT after mean subtraction, periodic Hann, coherent-gain-corrected one-sided peak amplitude; strongest eight peaks above the -120 dB display floor with at least 8 dB prominence; no zero padding | Bin-centered isolated-tone amplitude is exact; leakage and scalloping affect other tones. Bin spacing is not two-tone resolving power. Both full band and a fixed 0-500 Hz detail are shown. |
| Welch PSD | Mean Hann periodograms, 1,024 samples and 256-sample hop, reduced explicitly for shorter intervals; density in FS squared/Hz, integrated power, centroid, flatness and frame count | Overlapping frames are not independent. Resolution changes with native sampling rate. Tail samples outside complete frames are counted explicitly. |
| STFT PSD | Same window/frame/hop and density scaling as Welch, with fixed -130 to 0 dB color limits and native Nyquist frequency | Time-frequency resolution tradeoff and edge coverage remain explicit. Single-frame plots use explicit time/frequency cell edges so short input does not render as a blank chart. |
| Band power | Sum of PSD bins times frequency-bin width in fixed bands clipped at Nyquist; absolute power and fraction of total Welch power | Bands use bin centers, with Nyquist included in the final band. No inferred mechanical components or calibrated sound-pressure level. |
| Hilbert envelope and modulation FFT | Broadband analytic-signal magnitude by default; optional explicit fourth-order zero-phase Butterworth bandpass; exclude 50 ms at both edges; FFT of the centered envelope up to 500 Hz | Broadband beating and edge effects can create modulation peaks. The band is not automatically selected from fault labels. Short inputs report unavailable envelope analysis. |
| Autocorrelation | FFT-based correlation of mean-centered data, normalized by zero-lag energy, up to 100 ms; strongest positive nonzero-lag peak | Biased normalization and finite observation length. A repeated waveform period does not establish shaft RPM. |

For amplitude $a>0$, the report uses $20\log_{10}(a)$ dB relative to 1 FS. RMS uses 1 FS RMS as reference; a full-scale sine therefore has RMS -3.0103 dB under this convention. This is not the alternative convention in which a full-scale sine's RMS is assigned 0 dBFS. PSD uses $10\log_{10}(P)$ relative to 1 FS squared/Hz. Undefined logarithms and ratios for silent/constant input are null in JSON rather than invented finite measurements; plotting floors affect display only.

For a periodic Hann window $w$, one-sided FFT amplitude is $|\mathrm{FFT}(xw)|/\sum w$, doubled at positive frequencies except Nyquist. DC and Nyquist are not doubled. FFT bin spacing is $f_s/N$; Hann equivalent noise bandwidth is $f_s\sum w^2/(\sum w)^2$. The report exposes both values. Welch band integration uses the same one-sided PSD normalization, allowing the sum of band powers to be checked against integrated spectral power.

Absolute sound-pressure levels, SNR, causal mechanical diagnoses, order tracking and component-specific fault frequencies are intentionally absent. They require additional calibration, trustworthy noise/reference measurements, tachometer/RPM data or machine geometry that these files do not provide. No mel/wavelet rendering is added merely to increase image count.

## Prioritize Shape-Comparison Extensions

The existing seven views provide a reproducible baseline. Their diagnostic usefulness and robustness are still being evaluated; the [labeled comparison](DSP_LABELED_RESULTS.md) supports enriching the comparison representation before further inference. The following extensions are proposed and have not been implemented or validated.

| Priority | Extension | Information gained | Required check |
| --- | --- | --- | --- |
| 1 | Multiresolution Welch and STFT, with frame lengths specified in seconds and explicit bandwidth | Fine harmonic/sideband structure alongside fast transients | Synthetic neighboring tones, amplitude modulation and impulses; consistent physical resolution across native rates |
| 1 | Pairwise normalized spectral overlays, difference curves and per-band distance contributions | Identifies the regions responsible for a match or disagreement | Gain-change invariance within the linear range; explicit floors and low-energy handling; compare with the current uniformly weighted log-PSD distance |
| 1 | Within-recording distributions of shape features and regime stability | Median, quantiles, persistence and transient occupancy expose variability hidden by a whole-window average | Known synthetic transitions and same-source window dependence; quality indicators remain distinct from validated regime labels |
| 1 | Multi-reference class comparison with separate representative regimes | Measures proximity to several valid forms, within-class variation and the competing-class margin | Separate acquisitions for references, calibration and evaluation; disclose labeled-example counts and control unequal reference-bank sizes |
| 2 | Harmonic-family and sideband relationships; cepstrum, the inverse transform of the log-magnitude spectrum | Quantifies repeated spectral spacing and relative line patterns | Known harmonic fixtures and ambiguous fundamentals; retain absolute-frequency evidence and state uncertainty about mechanical interpretation |
| 2 | Band-specific envelope spectra and normalized modulation features | Separates modulation in distinct carrier bands and exposes repeated impacts | Predetermined or development-selected bands; distinguish modulation from beating; retain edge/filter transients and an unavailable state |
| 3 | Spectral kurtosis, measuring temporal impulsiveness per frequency band, and cyclic spectral coherence, measuring periodic relationships between spectral components | Candidate localization of transient or periodically modulated fault signatures | Evaluate only when earlier analyses leave a concrete gap; account for record duration, computation and nonspecific background impulses |

The fixed 1,024-sample Welch/STFT frame currently gives bin spacing of about 43.07 Hz at 44.1 kHz and 41.02 Hz at 42 kHz. With a periodic Hann window, equivalent noise bandwidth is approximately 1.5 times that spacing. The full-interval FFT already has much finer bin spacing, so the proposed improvement concerns stable spectral estimates and time-frequency evidence at several resolutions. Zero padding does not provide additional physical resolving power.

For a linear acquisition gain, mean-centering the log PSD already removes the constant level shift, subject to flooring and numerical limits. Position, microphone frequency response, reverberation and changed speed/load can modify the spectral shape itself. Evaluate robustness using actual acquisition variation and controlled gain/filter/noise perturbations, with clean baselines, bounded perturbations and clipping checks. Synthetic perturbations exercise the method; evidence about real acquisition transfer requires real recordings. Preserve features that discriminate fault classes when introducing invariances. Order tracking, which expresses frequencies relative to rotational speed, requires trustworthy speed information or a separately validated estimate.

The target comparative report should contain every candidate class and reference ID, quality/coverage flags, several independent shape comparisons, per-band contributions, time consistency, within-class ranges, the closest competing class and an explicit record of conflicting evidence. Provide typed numerical evidence plus a small set of aligned plots. Compare numerical-only classification with AI interpretation of the same evidence. Recognition errors, false rejections, wrong acceptances and human review load must be reported separately. Report completeness and model schema compliance remain technical checks.

## Outputs And Use

The command below processes a file already present in the workspace; it does not require a model endpoint. Use a fresh output name. The CLI prints its elapsed time, and each report records decode/analysis/plot/total durations.

```powershell
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_report --input data/visual-audio-exp011-v1/audio/2a1a4fc0edb8e810f1c8278c.wav --output artifacts/dsp-single-replay-v1 --recording-id R0001 --source-state original | Out-Host }
Measure-Command { & .\.venv\Scripts\python.exe -m scripts.dsp_report --suite configs/dsp-examples-v1.json --output artifacts/dsp-examples-replay-v1 | Out-Host }
```

Each report contains `report.html` (self-contained human view), `report.md` (deterministic measurement narrative), `evidence.json` (all interval metrics and limitations), `images/` (lossless 1200 by 700 RGB PNGs), `arrays/` (compressed numerical arrays for replay/inspection), `provenance.json` (restricted source identity/history), `manifest.json` (hashes, versions, configuration and timings) and `attempts.jsonl` (completion/failure ledger). The suite adds a linked browser index, registration and aggregate summary. Its four-example protected-data statement describes the supplied fixed example manifest, not an independent discovery of arbitrary custom source lineage.

The [packet contract](DSP_LLM_FORMAT.md) selects measurements and images for model comparison. Source provenance, raw filenames and publisher truth stay outside model inputs.

## Validation And Attempts

Thirteen new tests cover FFT amplitude/bin spacing/Hann bandwidth, doubled-amplitude +6.0206 dB behavior, non-doubled DC/Nyquist bins, integrated Welch/band power, equality of mean STFT PSD and Welch PSD, known 40 Hz amplitude modulation, autocorrelation periodicity, silence, nonfinite rejection, traceable level changes, native 44.1 kHz opposite-polarity stereo preservation, fixed plotting schedule, complete reports, hidden-filename exclusion, failed-attempt persistence, one-sample final tails, optional envelope filtering and nonblank single-frame STFT pixels. Synthetic fixtures validate calculations and software only.

Both real-data runs completed for all four datasets. The first set is retained at `artifacts/dsp-examples-v1/`; the second at `artifacts/dsp-examples-v2/`. Version 2 adds the fixed FFT detail, collapses long method notes in the browser and fixes single-frame/tiny-tail displays. All 125 numerical interval dictionaries, excluding image metadata, compare exactly across versions. All 212 files listed in the final manifests passed SHA-256 verification. No outcome-based parameter tuning or new source selection followed the first run.

Browser checks verified all 67 PNGs at 1200 by 700, nonblank pixels, navigation to Jin's final interval and no horizontal overflow at 1440/390-pixel widths. Development logs remain under `artifacts/dsp-*.log`; both report versions are preserved.
