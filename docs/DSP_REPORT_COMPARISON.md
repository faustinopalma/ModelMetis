# Whole-Report DSP Similarity

The restarted workflow generates one deterministic DSP report for every WAV, sends N known reports and one unknown report to the model, and asks for either the best similar known condition or a report different from every reference. The first real example returned `similar / C03`. This demonstrates execution and an inspectable comparison, not independently validated analytical correctness or physical fault classification.

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

A known condition is represented by one supplied reference WAV and an opaque condition ID such as `C01`; `R01` identifies its report. `Q01` is the unknown report. Reference IDs do not assert a mechanical diagnosis. The input specification accepts N >= 1 known conditions, with unique IDs, and exactly one unknown WAV. Paths resolve relative to the specification file.

The [DSP generator](DSP_PIPELINE.md) preserves native sample rate and individual channels. All interval measurements and every generated figure enter the request. The generator retains measurements for every five-second interval, including the tail, while detailed plots cover at most four fixed sampled intervals per channel. Thus a complete generated report does not mean that every interval of a long recording has a detailed plot. Full arrays stay local; model-facing floating-point summaries use seven significant digits. Source paths, hashes and explicit source offsets stay outside the prompt.

The model compares every reference using spectral shape, harmonic relationships, absolute frequency, band energy, envelope, periodicity and time evolution. It must produce exactly one comparison per reference and cite evidence from both that reference and the unknown. `similar` selects a known condition assessed as similar; `different` requires every reference to be assessed as different and a null selected condition. Refusal, truncation, invalid citations, network errors and deadline expiration are technical failures, not a third semantic outcome.

The qualitative similarity threshold is not calibrated. A valid output schema or an existing evidence ID does not establish that the interpretation is correct. This example does not use physical condition truth to score the answer and does not establish fault transfer across drone types. The earlier [EXP-012 results](DSP_LLM_RESULTS.md) remain a separate, negative classification experiment; its contract and implementation are unchanged.

## Run

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_dsp prepare --spec configs/dsp-similarity-example-v1.json --settings configs/dsp-sol-reuse-v1.json --output outputs/dsp-report-comparison-v2
.\.venv\Scripts\python.exe -m scripts.compare_dsp run --output outputs/dsp-report-comparison-v2
```

Preparation requires a new output directory and performs no model call. The supplied [example specification](../configs/dsp-similarity-example-v1.json) reuses the three frozen A reference WAVs and the first B query in the existing input order, without accessing drone C or selecting a query from new results. Original WAVs are local data, not published with this repository. Change the WAV paths for another comparison and use a new output directory for each attempt.

The request uses the existing pinned Sol deployment with low reasoning and a 4,096-token completion limit. Before the one-shot call, the runner checks the frozen file hashes, implementation, endpoint, subscription, tenant and deployed model identity. Entra authentication is acquired into memory; the saved request contains no Authorization header or token. A folder already attempted cannot be sent again automatically. The worker has a 180-second process deadline; interruption can leave remote execution or cost unknown.

The current packer rejects more than 50 images, 250,000 UTF-8 text bytes or a 10 MB request body. These are local admission limits, not a claim about Sol's maximum capacity. It never silently drops reports, intervals or generated figures to fit. Numerical arrays are deliberately excluded from the model representation. Sampling rates and durations may differ, but the declared DSP configuration must match. The workflow does not enforce independent physical acquisitions or reject identical reference/query PCM; those require an evaluation protocol when measuring accuracy.

## Observed Result

| Observation | Measured value |
| --- | --- |
| Real requests completed | 1/1; no retry and no technical failure |
| Input | 3 known WAVs + 1 unknown WAV; 0.5 seconds each, 16 kHz, one channel |
| Model-facing evidence | 32 original PNGs; 28,250 UTF-8 text bytes; 3,415,754 exact request bytes |
| Returned model | `gpt-5.6-sol-2026-07-09` |
| Returned comparison | C01 different; C02 different; C03 similar; selected C03 |
| Tokens | 41,216 input, none cached; 1,689 completion including 120 reasoning |
| Estimated list-price cost | USD 0.2185084; not an invoice |
| Worker elapsed time | 24.280 seconds; command elapsed 27.924 seconds |
| Analytical correctness | Not independently validated; no accuracy claim |

The explanation emphasized the relative 1:2 structure of Q01's 226/454 Hz lines versus R03's 286/572 Hz lines, corresponding autocorrelation lags of 4.375 versus 3.5 ms, and similar overall levels. These are the model's stated reasons; the exact answer and its per-reference differences remain in the local response files. No prompt retuning or additional paid comparison followed this answer.

Software checks cover variable N, complete interval/figure inclusion, explicit limits, binary response consistency, evidence IDs, frozen artifacts, exact HTTP body bytes and one-attempt protection. The four generated reports, index and readable response were checked at 1440px and 390px widths: all 32 report images loaded at both sizes and no page-level horizontal overflow was observed.