# Extended DSP And All-Diagram Experiments

**The model's errors mostly assign wrong classes: twelve of fourteen errors are unacceptable assignments, and only two are review-directed rejections.** Jin achieved 4/4 correct known labels and 1/4 correct excluded-class rejections; Ottawa achieved 2/8 and 3/8 respectively. Keep every DSP representation for inspection and defer pruning to a separately registered comparison. These measurements use previously consumed project acquisitions and do not establish fresh diagnostic generalization.

Applying the intended `different`-to-review policy yields six review-directed decisions overall: four correct excluded-class rejections and two false rejections. Eighteen decisions assign a class; twelve of those eighteen are wrong. This is a fixed paired known/excluded replay, not an estimate of production error prevalence, and human intervention was not executed.

The separate [diagram-attribution audit](DSP_DIAGRAM_AUDIT.md) requires all-view review and freezes reference-only priorities before presenting each query. On eight selected paired decisions, correctness stays 5/8, wrong assignments decrease from 2/8 to 0/8, and known-class false rejections increase from 1/4 to 3/4. Self-reported diagram importance is not measured predictive power: all six Ottawa decisions reject, often using accurate numerical differences across operating profiles. These results do not replace the twenty-four-decision measurements below or authorize pruning without a matched ablation.

Open the v14 comparison (local source: `outputs/audio-comparison-v14/index.html`) for simplified error review with one AI decision per case, Correct reference / Model choice buttons and no Set or Trial selectors. Its default filter shows all fourteen errors among twenty-four decisions over twelve query recordings; twelve references and all twenty-six diagram choices remain available. Other explicitly disables Model choice because no reference was selected, while the correct reference and browsing arrows remain usable. Excluded-class cases identify the withheld correct reference and their expected Other response, even when that reference is opened for human comparison. Detailed results (local source: `outputs/audio-comparison-v14/results.html`) retain expected/observed outcomes, explanations and exact request/response links. A/B playback uses the original registered WAV bytes. V13 retains the broader thirty-six-query numerical-control workbench and review notes. Earlier artifacts, model evidence and saved notes remain unchanged; v14 makes no inference calls.

## Every Analysis Family Has A Declared Implementation And Limit

The [extension module](../src/modelmetis/dsp_extensions.py) adds nineteen panels to the seven original per-interval views. Every panel has an entry in the [diagram guide](../src/modelmetis/dsp_guide.py). Missing input produces an explicit unavailable panel; no method is silently removed. The original DSP modules, old figures, datasets and historical requests remain unchanged. The selected sources are the same 48 mono ten-second recordings already used in the v8 workbench, not the complete dataset inventory.

| Panels | Implemented calculation | Interpretation boundary |
| --- | --- | --- |
| Five band envelopes and carrier/modulation map | Fourth-order zero-phase Butterworth bands at 100-500, 500-1,500, 1,500-4,000, 4,000-8,000 and 8,000-16,000 Hz; Hilbert envelope and squared envelope; mean-relative FFT amplitude; 100 ms edge exclusion | Bands reaching Nyquist are unavailable. Modulation is capped at 500 Hz and half the carrier-band width; unsupported map cells are masked. Beating can resemble fault modulation. |
| Real cepstrum | Inverse transform of the floored log-magnitude Hann spectrum; nonzero quefrencies through 100 ms | Quefrency q suggests spacing 1/q Hz, not component identity or validated RPM. |
| PSD estimators | Welch mean, Welch median and five DPSS tapers with time-bandwidth product 3; 100 ms frames | Multitaper smoothing bandwidth is 60 Hz. Curves share power-density units but differ in smoothing and outlier response; no uncertainty interval is supplied. |
| Persistence | Histogram of frame PSD level at each pooled frequency; percentages sum to 100 per frequency column | Retains distributions rather than chronology. Overlapping frames are dependent. |
| Harmonic spacing | Pairwise spacing histogram for up to 24 prominent peaks; candidate families with frequency tolerance | Peak-pair coincidences and missing fundamentals remain ambiguous. This is not a validated harmonic tracker or automatic bearing-frequency annotation. |
| STFT spectral kurtosis | E[P squared]/E[P] squared minus 2 over frames, with low-energy and endpoint exclusions | Complex Gaussian reference is asymptotically zero; finite-sample bias is not corrected. Background impulses and regime changes can also produce peaks. |
| Filter-bank impulsiveness | Thirty Butterworth bands across four dyadic levels; excess kurtosis of analytic-signal power | A transparent filter-bank variant, not the published Fast Kurtogram algorithm. All bands remain visible; no outcome-selected band is adopted. |
| Cyclic spectral coherence | STFT frequency-bin pairs with cyclic phase correction and normalized squared coherence; 10 Hz cyclic grid through 300 Hz | A direct bin-pair estimator, not Fast-SC. Deterministic tones also correlate; low-energy cells are masked and no significance threshold is calibrated. |
| Physical STFT and dominant ridge | 100 ms STFT plus strongest eligible frequency bin per frame | Display pools linear PSD; the ridge has no continuity model and is not an RPM estimate. |
| Reassigned STFT | Hann derivative and time-weighted transforms relocate spectral weight in time and frequency | Color is pooled spectral weight, not PSD. Threshold and retained weight are reported. |
| Morlet scalogram | PyWavelets complex Morlet `cmor1.5-1.0`; 48 logarithmic frequencies; physical-time coefficient scaling | Auxiliary anti-aliased integer decimation keeps analysis sampling at or below 16 kHz. The upper wavelet frequency is 0.3 times that rate; full edge support is masked. Other panels retain their declared native bandwidth. |
| Order spectrum and synchronous average | Positive independent RPM trace, angular resampling, declared anti-alias filtering and averaging of complete rotations | Both are implemented and synthetically tested but unavailable on these files, which have no supplied RPM trace. Synchronous averaging can suppress asynchronous bearing impacts. An order-RPM waterfall and tacholess RPM estimator are not implemented. |

The implementation reuses NumPy/SciPy and adds PyWavelets 1.8.0 to the native ARM64 runtime. The [dependency snapshot](../ml/requirements-dsp-extensions-windows-arm64.txt) includes the existing DSP pins. The separate x64 encoder runtime is unchanged. New analyses accept finite mono input up to an explicit 30-second limit and reject oversized input rather than truncating it. Multiple original channels require explicit selection in the surrounding workflow.

## The Model Receives A Reading Guide And Every Panel

The exact transmitted system prompt (local source: `outputs/audio-comparison-v14/prompt.txt`) defines each panel's axes, units, meaningful structures, missing-data states and interpretation limits; the response contract requires one comparison per visible condition with reference-specific and query-specific citations. It explains that the views are correlated, that a nearest reference is a forced ranking, and that gain normalization does not compensate microphone response, placement, speed or load. Reference-removal cases contain neither the removed class's report nor its numerical distances.

Each source contributes all 26 panels, including explicit unavailable panels, in two 2,400-by-1,520 contact sheets. Original 1,200-by-700 PNGs remain local; each sheet cell uses a declared 600-by-350 Lanczos derivative with an opaque evidence ID. The prompt uses high image detail. The original full-record overview is not an additional sheet panel because the workbench already uses the complete ten-second interval waveform. All original interval numerical measurements are included; extension curves are summarized by numerical extrema/largest bins and map statistics, with full extension arrays in local evidence JSON. Removing repeated prose and audit hashes from model text was transport compaction, not method pruning.

The AI helper [registers and executes the new campaign](../scripts/dsp_extended_ai.py) independently of the completed historical registrations. Exact request bytes, response bytes, settings, contracts and code bindings are retained. The [final review generator](../scripts/dsp_extended_review.py) validates the response against its raw content and citation contract before displaying it. Prompt compliance and valid citations are technical integrity checks, not proof of correct analytical reasoning.

## Numerical Screening And AI Correctness Are Separate Measurements

The offline screen computes a separate RMS distance for each representation, with no learned weights or acceptance radius. Line profiles use 256 interpolated points; maps use row means resampled to 256 points. Those descriptive reductions can discard important time-frequency structure and are not optimized classifiers. The baseline uses the existing gain-centered full-band Welch shape. Comparisons keep the original four Jin/eight Ottawa references fixed. No representation was removed after observing its score.

| Numerical representation | Jin correct | Jin wrong | Ottawa correct | Ottawa wrong |
| --- | --- | --- | --- | --- |
| Historical baseline | 20/20 | 0/20 | 2/16 | 14/16 |
| Envelope 1 | 7/20 | 13/20 | 3/16 | 13/16 |
| Envelope 2 | 12/20 | 8/20 | 2/16 | 14/16 |
| Envelope 3 | 4/20 | 16/20 | 1/16 | 15/16 |
| Envelope 4 | 5/20 | 15/20 | 1/16 | 15/16 |
| Envelope 5 | 10/20 | 10/20 | 1/16 | 15/16 |
| Modulation map | 11/20 | 9/20 | 2/16 | 14/16 |
| Cepstrum | 16/20 | 4/20 | 3/16 | 13/16 |
| PSD estimator curves | 20/20 | 0/20 | 5/16 | 11/16 |
| Persistence | 13/20 | 7/20 | 2/16 | 14/16 |
| Harmonic spacing | 4/20 | 16/20 | 2/16 | 14/16 |
| Spectral kurtosis | 10/20 | 10/20 | 1/16 | 15/16 |
| Filter-bank kurtosis | 9/20 | 11/20 | 3/16 | 13/16 |
| Cyclic coherence | 12/20 | 8/20 | 2/16 | 14/16 |
| Physical STFT profile | 20/20 | 0/20 | 4/16 | 12/16 |
| Dominant ridge | 4/20 | 16/20 | 1/16 | 15/16 |
| Reassigned profile | 18/20 | 2/20 | 4/16 | 12/16 |
| Wavelet profile | 10/20 | 10/20 | 4/16 | 12/16 |

The two RPM-dependent representations are unavailable on 20/20 Jin and 16/16 Ottawa queries; they produce no label and are excluded from neither source denominators nor the availability report. These are twenty separate control configurations over the same queries, including two unavailable controls, yielding 720 output records. There is no numerical rejection rule in this screen. Jin's twenty windows share eight direction/acquisition groups; Ottawa has sixteen selected acquisitions with the documented motor/class confounding.

The AI series contains one query per class: four right-direction Jin windows at offset zero and eight Ottawa profile-2 unloaded acquisitions. Each query is presented once with the full bank and once with its matching class removed. These are twelve selected query recordings and twenty-four decisions, not twenty-four independent acquisitions. The fixed selection was not changed after observing answers.

| Dataset | Correct known label | Wrong known label | False rejection | Correct excluded-class rejection | Wrong acceptance |
| --- | --- | --- | --- | --- | --- |
| Jin, all-diagram Sol | 4/4 | 0/4 | 0/4 | 1/4 | 3/4 |
| Ottawa, all-diagram Sol | 2/8 | 4/8 | 2/8 | 3/8 | 5/8 |

All twenty-four decisions passed structured-output and reference/query citation checks. No full reference-set numerical or AI result establishes an acceptance threshold. The added panels have not demonstrated simultaneous reliable recognition and rejection, and the changed prompt plus added representations form a combined intervention rather than an isolated attribution test. The older [labeled results](DSP_LABELED_RESULTS.md) and [offline shape replay](DSP_OFFLINE_RESULTS.md) remain separate baselines.

## Attempts And Throughput Remediation Remain Traceable

Local preparation v1 stopped at its 20 MB byte-admission guard before any HTTP call. The guard increased to 64 MB without dropping figures. AI preparation v2's first request received HTTP 429. After repeated text/audit metadata were compacted, v3 completed five decisions and then received another HTTP 429. Both service rejections have no token usage or established cost; their raw responses and request hashes are retained.

The existing DataZoneStandard deployment capacity increased from 50 to 100 kTPM using the unchanged [Bicep template](../infra/dsp-existing-account.bicep) with `capacity=100`. A what-if showed only the deployment capacity change; the ARM operation `modelmetis-dsp-throughput-100` succeeded and a fresh read verified capacity 100, pinned Sol version, DataZoneStandard SKU and NoAutoUpgrade. Other resources were untouched. Global Standard quota remained fully allocated and its pending quota request was not resubmitted. Future use of the template default would restore capacity 50, so pass the intended capacity explicitly.

The continuation at `outputs/dsp-extended-ai-v4` reuses five successful v3 receipts whose request bytes are identical, and completes the remaining nineteen cases. Reused receipts are not new calls. Across the complete work there are twenty-six actual HTTP attempts: twenty-four completed decisions and two 429 responses. The final accepted responses report 1,551,988 prompt tokens and 47,522 completion tokens. The eight Jin calls have a combined list-price estimate of USD 1.78383480. Sixteen completed Ottawa calls exceed the legacy 64,000-prompt-token pricing guard; their usage is retained but their cost is unestablished by that calculator. USD 1.78383480 is therefore a partial estimate, not total experiment cost. No monetary cap was imposed.

The Foundry skill dependency check could not install its azd extension because a dependency was unavailable. This workflow uses the existing direct Entra-authenticated HTTP runner, not an azd agent workflow; live target checks and all twenty-four completed responses verified that path. No agent resource was created.

## Verification And Reproduction Preserve The Evidence

The complete repository suite passed 203 tests with three existing dependency warnings. Focused tests validate modulation recovery and gain behavior, cepstral spacing, integrated multitaper power, persistence percentages, cyclic periodicity, reassignment localization, wavelet masks, impulsiveness, RPM-based order recovery, unavailable cases, strict JSON, rendered figures, exact HTTP bytes, token exclusion, one-attempt protection and raw-response citation binding. Passing synthetic checks does not demonstrate real fault-diagnosis capability.

All 1,064 files listed in the offline manifest and all twenty-four final AI response bindings verified. The workbench was checked at 1,440 and 390 pixels with loaded figures and no page-level overflow on both datasets, including unavailable RPM panels. Reference switching retained the input; registered audio played without a media error; the Ottawa AI error filter reported 6/8. Historical output directories remain unchanged.

Independent recounting reconciled all 720 numerical output records. All 912 extension PNGs were nonblank at 1,200 by 700 pixels; 816 panels contained available analyses and 96 explicitly reported missing RPM. A/B alternation and image enlargement passed browser checks. The results page contained all 24 decision rows at desktop/mobile widths. These are artifact and interaction checks, separate from analytical correctness.

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements-dsp-extensions-windows-arm64.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.dsp_extended_experiment --output outputs/dsp-extended-reproduction
.\.venv\Scripts\python.exe -m scripts.dsp_extended_review --source outputs/dsp-extended-v1 --ai-source outputs/dsp-extended-ai-v4 --output outputs/audio-comparison-reproduction
```

Reproduction uses fresh output folders. The complete source collection and intermediate artifacts remain local; the [curated public snapshot](../examples/README.md) publishes selected consumed audio, figures, decisions and comparisons under the [publication policy](PUBLICATION.md). Repeating the recorded data is replay evidence. The paid runner's `prepare` action is local; `run` submits requests. A new scientific series requires its own selection and registration, with accepted-label errors, false rejections, unknown acceptance and human workload scored separately. Progressive human enrichment has not been executed.

## Method References Support Implementation Rather Than Accuracy Claims

- [MathWorks envelope spectrum](https://www.mathworks.com/help/signal/ref/envspectrum.html): band demodulation and ordinary envelope interpretation.
- [SpectraQuest envelope and cepstrum analyses](https://spectraquest.com/rotating-machinery-fault-diagnosis-techniques-envelope-and-cepstrum-analyses/): harmonic families and sidebands.
- [MathWorks spectral representations](https://www.mathworks.com/help/signal/ref/pspectrum.html): persistence and reassignment.
- [MathWorks kurtogram](https://www.mathworks.com/help/signal/ref/kurtogram.html) and [Antoni Fast-SC](https://www.mathworks.com/matlabcentral/fileexchange/60561-fast_sc-x-nw-alpha_max-fs-opt): related published methods; the present transparent variants are not those algorithms.
- [MNE multitaper documentation](https://mne.tools/stable/generated/mne.time_frequency.psd_array_multitaper.html): DPSS bandwidth/variance tradeoff; this implementation uses SciPy DPSS and Welch.
- [PyWavelets CWT](https://pywavelets.readthedocs.io/en/latest/ref/cwt.html): wavelet frequency, scaling and sampling constraints.
- [MathWorks order analysis](https://www.mathworks.com/help/signal/ref/rpmordermap.html): angular resampling and independent RPM requirements.
- [DCASE acoustic monitoring](https://dcase.community/challenge2024/task-first-shot-unsupervised-anomalous-sound-detection-for-machine-condition-monitoring): acoustic domain shifts and limits of transferring vibration-based expectations to microphones.
