# Whole-Report DSP Similarity

The labeled experiments show useful recognition on Jin and an unresolved recognition/rejection tradeoff. Numerical comparison evidence raised Jin development recognition from 5/8 to 8/8 and achieved 11/12 correct labels on the reserved direction, with 2/4 correct excluded-class rejections. A calibrated replay improved rejection to 4/4 while recognition fell to 9/12. Ottawa recognition was 4/16. The combined acceptance criteria remain unmet; see [the labeled results](DSP_LABELED_RESULTS.md).

The workflow generates one deterministic DSP report per WAV, supplies N labeled reference reports and one unknown report, and returns a matching known condition or `different`. The local result index is `outputs/dsp-labeled-results-v1/index.html`; reference audio is available under `outputs/dsp-jin-v1/reference-audio` and `outputs/dsp-ottawa-v1/reference-audio`.

## Inspect The Example

The local output is `outputs/dsp-report-comparison-v1/index.html`. Open it to inspect all four reports, the exact prompt, all transmitted measurements and images, and the actual service response. The output directory is ignored by Git. The public [result record](../ml/dsp-similarity-example-v1-results.json) contains nonsecret execution metadata only.

| Folder | Contents |
| --- | --- |
| `01_dsp/R01`, `R02`, `R03`, `Q01` | Complete HTML/Markdown report, original analytical PNGs, numerical arrays, measurements, provenance and artifact manifest for each WAV |
| `02_model/prompt.txt` | System prompt text; the exact wire string is in `request.json` |
| `02_model/reports.json` | All model-facing interval measurements, report configuration, coverage and figure descriptions |
| `02_model/request.json` | Exact transmitted JSON bytes, including original PNG data URLs and structured-output schema |
| `02_model/request-readable.json` | Clearly marked inspection copy with local image paths replacing data URLs |
| `02_model/images`, `image-manifest.json` | Every transmitted PNG, image IDs, dimensions and SHA-256 hashes |
| `03_response` | Raw service response, parsed decision, readable HTML/Markdown answer and execution receipt |
| `audit` | Source mapping and preparation specification, outside the model input |

## Contract

A known condition is represented by one supplied reference WAV and a condition ID such as `C01`; `R01` identifies its report. An optional `label` supplies the publisher class name. `Q01` identifies the unknown report. The input specification accepts N >= 1 unique known conditions and exactly one unknown WAV. Paths resolve relative to the specification file. Query truth stays in a separate evaluator input.

The [DSP generator](DSP_PIPELINE.md) preserves native sample rate and individual channels. All interval measurements and every generated figure enter the request. The generator retains measurements for every five-second interval, including the tail, while detailed plots cover at most four fixed sampled intervals per channel. Thus a complete generated report does not mean that every interval of a long recording has a detailed plot. Full arrays stay local; model-facing floating-point summaries use seven significant digits. Source paths, hashes and explicit source offsets stay outside the prompt.

The model compares every reference using spectral shape, harmonic relationships, absolute frequency, band energy, envelope, periodicity and time evolution. It must produce exactly one comparison per reference and cite evidence from both that reference and the unknown. `similar` selects a known condition assessed as similar; `different` requires every reference to be assessed as different and a null selected condition. Refusal, truncation, invalid citations, network errors and deadline expiration are recorded separately as technical failures.

The basic prompt uses qualitative similarity. The labeled evaluator scores the returned condition against publisher truth. Optional numerical evidence supplies gain-centered Welch spectral distances. The calibrated variant uses additional labeled development windows to estimate a separate acceptance threshold for each class. The earlier [EXP-012 results](DSP_LLM_RESULTS.md) retain their original classification contract and outcomes.

## Run

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_dsp prepare --spec configs/dsp-similarity-example-v1.json --settings configs/dsp-sol-reuse-v1.json --output outputs/dsp-report-comparison-v2
.\.venv\Scripts\python.exe -m scripts.compare_dsp run --output outputs/dsp-report-comparison-v2
```

Preparation requires a new output directory and performs no model call. The supplied [example specification](../configs/dsp-similarity-example-v1.json) reuses the three frozen A reference WAVs and the first B query in the existing input order, without accessing drone C or selecting a query from new results. Original WAVs are local data, not published with this repository. Change the WAV paths for another comparison and use a new output directory for each attempt.

The request uses the existing pinned Sol deployment with low reasoning and a 4,096-token completion limit. Before the one-shot call, the runner checks the frozen file hashes, implementation, endpoint, subscription, tenant and deployed model identity. Entra authentication is acquired into memory; the saved request contains no Authorization header or token. A folder already attempted cannot be sent again automatically. The worker has a 180-second process deadline; interruption can leave remote execution or cost unknown.

Default admission limits are 50 images, 250,000 UTF-8 text bytes and 10 MB per request. Sol explicitly rejected a 72-image request with a 50-image maximum. Settings can select lossless vertical pairs or compact contact sheets; the contact-sheet variant preserves every figure at up to 600 by 350 pixels, records original hashes and dimensions, and retains all original figures locally. Numerical measurements remain in the request. Image detail, byte limits and completion limits are explicit per preparation. The labeled experiments use ten-second analysis intervals, contact sheets and up to 8,192 completion tokens. Cached report reuse verifies source hashes and DSP configuration. The labeled registration checks source-file overlap and available acquisition groups; physical independence remains a dataset-specific limitation.

## Observed Result

| Observation | Measured value |
| --- | --- |
| Real requests completed | 1/1; no retry and no technical failure |
| Input | 3 known WAVs + 1 unknown WAV; 0.5 seconds each, 16 kHz, one channel |
| Model-facing evidence | 32 original PNGs; 28,250 UTF-8 text bytes; 3,415,754 exact request bytes |
| Returned model | `gpt-5.6-sol-2026-07-09` |
| Returned comparison | C01 different; C02 different; C03 similar; selected C03 |
| Tokens | 41,216 input, none cached; 1,689 completion including 120 reasoning |
| Estimated list-price cost | USD 0.2185084 |
| Worker elapsed time | 24.280 seconds; command elapsed 27.924 seconds |
| Analytical correctness | Not independently validated; no accuracy claim |

The explanation emphasized the relative 1:2 structure of Q01's 226/454 Hz lines versus R03's 286/572 Hz lines, corresponding autocorrelation lags of 4.375 versus 3.5 ms, and similar overall levels. The exact answer remains in its immutable local bundle. Subsequent labeled experiments use separate registrations and folders.

Software checks cover variable N, complete interval/figure inclusion, explicit limits, binary response consistency, evidence IDs, frozen artifacts, exact HTTP body bytes and one-attempt protection. The four generated reports, index and readable response were checked at 1440px and 390px widths: all 32 report images loaded at both sizes and no page-level horizontal overflow was observed.