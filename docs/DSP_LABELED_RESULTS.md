# Labeled DSP Comparison Results

**The complete known-match-or-different requirement remains unmet.** On Jin, adding explicit spectral distances to full DSP reports produced 11/12 correct known labels and 2/4 correct excluded-class rejections. A class-calibrated replay produced 9/12 and 4/4 respectively. Ottawa produced 4/16 correct labels. The useful signal is spectral separability on Jin; reliable simultaneous recognition and rejection requires broader representative labeled acquisitions and a fresh evaluation set.

The separate [offline multi-reference replay](DSP_OFFLINE_RESULTS.md) evaluates deterministic forced-label controls on previously consumed Jin inputs, without further AI calls. Its baseline achieves 12/12, while added representations achieve 9-12/12; acceptance/rejection remains unmeasured there. These results do not alter the historical decisions, gates or costs below.

## Inspect Every Input And Answer

Open `outputs/dsp-labeled-results-v1/index.html` for the expected label, actual prediction and outcome of every request. Each row links to its complete reports, exact prompt, transmitted JSON, image derivatives and raw model response. The index also links to both reference-audio galleries and case lists. Source WAV copies match the registered hashes; embedded playback uses the same bytes. Outputs, source mappings and credential caches remain local and ignored by Git.

## Correctness Is Measured Against Publisher Labels

| Dataset and method | Evaluation scope | Correct known label | Wrong known label | False rejection | Correct excluded-class rejection | Wrong acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| Ottawa, report comparison | Development | 4/16 | 12/16 | 0/16 | Unmeasured | Unmeasured |
| Jin, report comparison | Development | 5/8 | 3/8 | 0/8 | Unmeasured | Unmeasured |
| Jin, reports plus numerical distances | Development | 8/8 | 0/8 | 0/8 | Unmeasured | Unmeasured |
| Jin, reports plus numerical distances | Reserved direction within this run | 11/12 | 0/12 | 1/12 | 2/4 | 2/4 |
| Jin, class-calibrated rule | Exploratory replay after inspecting the reserved result | 9/12 | 0/12 | 3/12 | 4/4 | 0/4 |

All 64 completed classifications have valid reference-specific and query-specific citations; this is an integrity check. Correctness in the table comes from the returned label or rejection compared with publisher truth. Four additional technical failures produced no usable decision: one image-count rejection, two token-rate rejections and one completion truncated after 4,096 reasoning tokens.

The recognition gate was 14/16 for Ottawa development and 7/8 for Jin development, with at least one correct case per class. The Jin reserved gate was 11/12 known labels and 4/4 excluded-class rejections. Neither tested Jin variant passed both reserved criteria. The calibrated rule correctly rejected all magnet-fracture queries when that class was excluded, but also rejected all three magnet-fracture queries when its reference was present.

## Reference Cases Cover Each Evaluated Taxonomy

Ottawa UOEMD-VAFCVS v2, DOI `10.17632/msxs4vj48g.2`, provides 128 labeled ten-second microphone acquisitions across eight conditions, eight speed profiles and two loads. The selected references use profile 1 without load; development uses profile 2 under both loads. Profile 8 was reserved here and remained unused by this pipeline because the development gate failed. Earlier project experiments consumed profile 8. The importer exported microphone column 2 as mono 42 kHz PCM16 with per-acquisition peak normalization to 0.95.

| ID | Publisher class | Reference acquisition |
| --- | --- | --- |
| C01 | healthy | H_H_1_0 |
| C02 | rotor_unbalance | R_U_1_0 |
| C03 | rotor_misalignment | R_M_1_0 |
| C04 | stator_winding | S_W_1_0 |
| C05 | voltage_unbalance | V_U_1_0 |
| C06 | bowed_rotor | B_R_1_0 |
| C07 | broken_rotor_bars | K_A_1_0 |
| C08 | faulty_bearing | F_B_1_0 |

Jin v1, DOI `10.17632/9dpmkgpncw.1`, provides four labeled motor conditions from front, left and right microphone directions. References use the first ten seconds of the front recordings. Development uses left windows at 0 and 120 seconds; reserved evaluation uses right windows at 0, 120 and 240 seconds. Each input WAV is a complete ten-second window from the existing canonical package, mono 44.1 kHz PCM16 with DC removal and peak normalization to 0.95. Original recordings last approximately ten minutes. Attribution: Linjie Jin, CC BY 4.0. Ottawa attribution: Mert Sehri and Patrick Dumond, CC BY 4.0.

| ID | Publisher class | Reference acquisition and offset |
| --- | --- | --- |
| C01 | excess_hall_adhesive | b2f10m_01.wav, 0 s |
| C02 | healthy | nf10m.wav, 0 s |
| C03 | magnet_fracture | b1f10m_01.wav, 0 s |
| C04 | tight_bearing | b3f10m_01.wav, 0 s |

Every known-class request contains all reference classes. Each excluded-class request deliberately removes the reference matching the query's publisher class; the expected answer becomes `different`. This tests rejection under reference removal. It provides limited evidence about genuinely new fault mechanisms. Datasets with missing or unverified condition labels are ineligible for correctness evaluation under this protocol. AI Mechanic and drone were cataloged but were outside this bounded two-dataset experiment; protected drone C remained untouched.

## Numerical Evidence Explains The Improvement

The comparison computes a Welch power spectral density vector for each interval, converts it to decibels, subtracts its mean across frequency bins and averages vectors across intervals and channels. Distance is the root mean square difference between two resulting vectors. All frequency bins have equal weight. Constant gain is removed; frequency-dependent microphone transfer remains a possible confound.

On Ottawa development, nearest-reference distance yielded 2/16 correct with all bins, 2/16 above 500 Hz and 3/16 above 2 kHz. On Jin development the corresponding counts were 8/8, 8/8 and 7/8. The model's distance-assisted iteration therefore uses numerical evidence already sufficient for the eight Jin development decisions. An additional benefit from the language model over the numerical classifier has not been demonstrated.

Six global radius fractions were evaluated on eight known and eight simulated excluded-class development cases. The best total was 12/16. Class-specific thresholds used each class's maximum observed development distance multiplied by one of six fixed margins. Margins 1.0, 1.05, 1.1 and 1.2 achieved 16/16; 1.25 achieved 15/16 and 1.5 achieved 13/16. The deterministic tie-break selected the largest successful margin, 1.2. Thresholds were C01 3.377359 dB, C02 3.623526 dB, C03 3.227635 dB and C04 2.463183 dB. This consumes eight additional publisher-labeled development windows beyond the four reference labels. The model receives these thresholds and applies the closest-reference acceptance rule while explaining the evidence.

## Evidence Limits Control The Conclusion

Jin's twelve reserved windows share four original right-direction acquisitions. Unit and session independence are undocumented, and original healthy/fault files differ in PCM16/FLOAT encoding. The canonical export removes the container difference while acquisition artifacts can remain. These recordings had already been used in earlier project experiments. The first reserved evaluation was isolated from this run's development tuning; it still constitutes previously consumed project evidence. The calibrated replay followed inspection of that result and remains explicitly exploratory.

Ottawa's motor identity can be confounded with fault class, and the same motor population recurs across operating profiles. A single reference per condition failed to capture profile variation. A stronger next experiment requires multiple independent acquisitions for each condition and operating regime, with calibration and confirmation groups separated before selection. Recognition and rejection should be evaluated jointly on that fresh set.

## Execution And Reproduction

The run made 68 HTTP attempts: 64 complete responses, one truncated paid response and three service rejections with missing token usage. Known list-price consumption totals USD 8.43773744; costs for the three usage-free responses remain unestablished. The returned model for completed calls was the pinned Sol deployment. All request/response byte hashes and all completed-answer reference/query citations were checked. Authentication tokens remain in process memory.

Initial full reports exceeded the service's 50-image limit. Lossless pairs reduced 72 images to 36 but hit token-rate admission. Compact 1200-by-1400 contact sheets place each original figure in a 600-by-350 cell with declared Lanczos resizing. All figures and all numerical summaries remain represented; original PNGs and arrays remain local. The eight-reference Ottawa request needs nine sheets; Jin needs five. Completion capacity increased to 8,192 after a 4,096-token reasoning-only truncation. Every technical attempt is retained separately.

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_dsp_similarity register --dataset jin --output outputs/dsp-jin-new
.\.venv\Scripts\python.exe -m scripts.evaluate_dsp_similarity new-round --output outputs/dsp-jin-new --round 01 --numerical-comparison
.\.venv\Scripts\python.exe -m scripts.evaluate_dsp_similarity run --output outputs/dsp-jin-new --round 01 --phase development --limit 8
.\.venv\Scripts\python.exe -m scripts.evaluate_dsp_similarity evaluate --output outputs/dsp-jin-new --round 01 --phase development
```

Registration and reporting are local operations. `run` submits paid requests and requires the existing pinned endpoint and a valid Entra session. Existing attempted bundles are preserved. Repeating consumed data provides replay evidence; a fresh confirmation claim requires fresh acquisitions. Prompt-source cleanup changes reusable wording while historical request JSON retains the exact transmitted text.
