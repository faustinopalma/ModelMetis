# EXP-011 Results: Visual Access Blocked

The STFT tool is verified offline. The real-data numerical control returned indeterminate on all 12 registered trials, providing zero coverage. The visual comparison did not run: the authorized ModelMetis Azure resource has no GPT-5.6 deployment. The feasibility verdict is **inconclusive**, with no model promotion, silver collection, specialist training or routing. The next requirement is an explicitly authorized, fixed-version image-capable endpoint, not more human reference labels.

Completed September 29, 2026, from handoff commit `03418cfd6907752726b1b904de3daa30523df63e`. The original dirty worktree was preserved. See the [preregistered protocol](VISUAL_AUDIO_EXPERIMENT.md), [renderer](../src/modelmetis/visual_audio.py), [CLI](../scripts/visual_audio.py), [32 focused tests](../tests/test_visual_audio.py), and [unmodified aggregate](../ml/visual-audio-exp011-v1.json). This is the handoff's permitted offline fallback, not completion of a real visual feasibility experiment.

## Measured Results

| Outcome | Welch: known trials | Welch: unknown trials | Visual model |
| --- | ---: | ---: | --- |
| Correct known assignment | 0/9 | Not applicable | Not executed |
| Wrong known assignment | 0/9 | Not applicable | Not executed |
| Known falsely rejected as outside-reference | 0/9 | Not applicable | Not executed |
| Unknown falsely accepted as known | Not applicable | 0/3 | Not executed |
| Correct outside-reference decision | Not applicable | 0/3 | Not executed |
| Indeterminate | 9/9 | 3/3 | Not executed |
| Technical inference/control failures | 0/9 | 0/3 | 0 submitted requests |

Both known-label coverage and non-abstaining decision coverage were 0/12. Accepted-label error is undefined because no label was accepted. Zero false acceptance is not evidence of useful novelty detection when every unknown trial is indeterminate. The all-known fold produced three abstentions; each of the three whole-condition holdout folds also produced three abstentions. Each query condition accounts for four repeated decisions, all indeterminate.

| Evaluator truth | Predicted C01 | Predicted C02 | Predicted C03 | Outside-reference | Indeterminate | Technical failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 represented | 0 | 0 | 0 | 0 | 3 | 0 |
| C02 represented | 0 | 0 | 0 | 0 | 3 | 0 |
| C03 represented | 0 | 0 | 0 | 0 | 3 | 0 |
| Entire condition excluded | 0 | 0 | 0 | 0 | 3 | 0 |

All nearest-reference distances were below the frozen 12 dB rejection threshold. Nearest/second-nearest gaps ranged from approximately 0.041 to 1.779 dB, always below the frozen 2 dB ambiguity margin. No threshold was changed after this result. These are signal-comparison distances, not diagnostic probabilities.

The denominator is 12 query/reference-set trials over three distinct half-second B clips, not 12 independent acquisitions. There is one reference drone and one query drone; original take lineage is unknown. Hardware type, background mixtures and recording setup remain confounded. B is already development data. No C archive or C inventory rows were accessed. No acquisition-level confidence interval or false-alerts-per-hour estimate is justified.

## Data And Rendering

The six selected originals were re-extracted without peak normalization or DC removal. Both complete A/B archive SHA-256 values matched the earlier audit, and all six decoded PCM hashes matched the source inventory. Five selected containers are WAV; one is FLAC under a WAV filename. All are mono, 16 kHz, 24-bit PCM, 8,000 frames. There were no silent windows, clipped samples, resampling operations, channel reductions or padded samples in the real-data experiment. Every selected clip was retained; there was no reselection after seeing a prediction.

The [frozen rendering configuration](../configs/visual-audio-stft-v1.json) produces only STFT power spectral density images. All images use identical axes, digital full-scale power reference, color limits, colormap and dimensions. Welch never produces an image. Source provenance, grouping, offsets and hashes live in the local manifest; query answers live in a separate sealed file. Prepared model messages contain only neutral reference IDs, a neutral query marker, the shared prompt and metadata-free PNG bytes. Each holdout removes the entire omitted condition from both images and text. Twelve stateless message sets contain 39 image occurrences from six unique images; none has been submitted.

Signal tests establish the 1 kHz peak location, power integration, a 6.0206 dB increase on doubled amplitude, transient localization, unnormalized level differences, deterministic PNG bytes, valid-duration tails, overlap offsets, silence, positive/negative PCM clipping, explicit channel/resampling policies, truncated/corrupt decoding, split checks, strict response validation and evaluator denominators. A synthetic end-to-end test checks preparation bindings, complete-condition holdout and offline reporting; it is not acoustic diagnosis evidence. STFT frames have no boundary extension, so full-window observation near segment edges is limited. Fixed windows do not establish homogeneous regimes.

Local QA artifacts contain a 1/3 kHz two-tone signal with an impulse, its 512 by 384 resized image, and a six-image overview. The [local preview generator](../scripts/preview_visual_audio.py) embeds the exact original PNG bytes after checking their hashes. Browser checks loaded all six at their natural 1024 by 768 dimensions, verified the enlargement dialog and found no horizontal overflow at 1440- and 390-pixel viewport widths. This validates local display and resizing only. Readability and preprocessing inside the actual GPT-5.6 service remain unverified because nothing was sent.

## Model Access

Read-only discovery in the existing authorized resource returned only `modelmetis-audio-teacher`, OpenAI `gpt-audio-1.5`, version `2026-02-23`, state Succeeded, upgrade policy NoAutoUpgrade. Its catalog lists `gpt-5.6-sol`, `gpt-5.6-luna` and `gpt-5.6-terra`, all version `2026-07-09`. Catalog presence does not establish an accessible deployment or image inference compatibility.

The [official Azure model page](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure#gpt-56), fetched September 29, lists image processing and structured outputs for `gpt-5.6-luna`; this is the recorded candidate. The [vision guide](https://learn.microsoft.com/azure/foundry/openai/how-to/gpt-with-vision) describes low-resolution processing and additional 512-pixel segments for `detail=high`. That generic description is not verified Luna-specific preprocessing. The live image contract, actual returned identity, output schema, model latency and price basis still require endpoint verification and one bounded synthetic transport probe before real evaluation.

No resource, model deployment, firewall or role assignment was created or modified. No unrelated workspace Azure profile was reused. No alternative model was silently selected. To unblock the real experiment, supply access to an existing authorized GPT-5.6 image-capable deployment with exact provider/model/version, or explicitly authorize its provisioning and processing location. Credentials must remain in a secure local authentication path. An eventual independent-acquisition confirmation additionally requires documented original session/recording lineage and replicated units; this proxy cannot supply that evidence.

## Time, Cost And Human Work

| Operation | Observed time |
| --- | ---: |
| Verify/extract A | 24.266 s |
| Verify/extract B | 23.038 s |
| Prepare all sources and registration | 48.983 s internal; 50.483 s command wall time |
| Render six clips | 1.010 s renderer; 1.043 s enclosing operation |
| Decode and extract Welch features | 0.092 s |
| Twelve numerical decisions | 0.002120 s total; 0.000163 s median |
| Offline comparison including payload serialization | 2.500 s internal; 3.927 s command wall time |
| Sealed evaluation | 0.032 s internal; 1.269 s command wall time |
| Generate self-contained preview | 0.104 s internal; 0.384 s command including lint |

These are single local timings, not controlled throughput measurements. Visual latency and tokens are unmeasured. Inference expenditure is zero because no inference was requested; this is not a price estimate for the proposed model. No billing claim includes resource inventory operations or local compute. Candidate price provenance is explicitly not verified.

Three publisher reference annotations simulate the initial human references. There were zero new human diagnoses, extra calibration labels, query corrections or physical verifications. Human minutes were not measured and are not inferred from automation wall time. Visual inspection by the user is not a physical diagnosis.

## Attempt Ledger

All experimental attempts are retained in new ignored directories, with `attempts.jsonl` operation timing and immutable registrations. The following includes failed development/discovery commands; none was treated as a model result.

| Attempt | Outcome | Wall time |
| --- | --- | ---: |
| Initial Git status/HEAD | Dirty worktree recorded; expected handoff commit | 0.151 s |
| Full pre-edit pytest | 120 passed, three existing warnings; pytest 13.18 s | 14.522 s |
| Ruff and initial runtime inventory | Ruff passed; package metadata probe stopped on missing Pillow; x64 Python checked | 1.202 s |
| Initial STFT tests | 13 passed | 1.649 s |
| Corrected package inventory | ARM64 NumPy/SciPy/SoundFile/PyAV present; Pillow/Matplotlib absent | 0.772 s |
| Renderer dependencies | Installed Matplotlib 3.10.8 and Pillow 12.3.0 in existing ARM64 environment | 71.238 s measured tool interval, including orchestration |
| Existing deployment discovery | Only gpt-audio-1.5 deployed | 4.629 s |
| Decoder/PNG tests | 19 passed | 7.960 s |
| First GPT-5.6 catalog query | Failed: query assumed a nested model object | 5.422 s |
| Corrected catalog query | Three exact GPT-5.6 IDs and versions returned | 4.650 s |
| Numerical/contract tests | 26 passed | 3.040 s |
| Initial runner gate | 28 passed; Ruff rejected one 102-character line | 3.915 s |
| Repaired runner gate | 31 passed; Ruff clean | 3.426 s |
| Source preparation v1 | Completed; no data fallback or reselection | 50.483 s |
| Offline comparison v1 | Completed; 12 abstentions, zero model calls | 3.927 s |
| Evaluation v1 | Completed; inconclusive visual verdict | 1.269 s |
| Local image QA generation | Original signal, resized signal and six-image overview generated | 1.850 s |
| Focused end-to-end gate | 32 passed; Ruff clean | 5.340 s |
| Chat-error log search with rg | Failed because rg is not installed; PowerShell fallback used | 0.187 s |
| PowerShell log search | Reported request ID absent from available session log | 0.028 s |
| Self-contained gallery generation | Six original PNGs; Ruff clean | 0.384 s |
| Final full pytest and Ruff | 152 passed, three unchanged warnings; pytest 13.50 s; Ruff clean | 14.883 s |

The user also reported a Copilot HTTP 400 `invalid_request_body` with an upstream file-download 404 after chat image-preview attempts. Request identifiers were not found in the available session debug log, so a specific backend root cause is unconfirmed. This is not an Azure model inference failure: there were no Azure inference calls. The local HTML viewer avoids attaching images to chat and was verified to load. No editor settings or logs were reset.

## Evidence Locations

Local originals, masked inputs, sealed query truth and the registration are in `data/visual-audio-exp011-v1/`. Images, twelve unsubmitted message files, numerical predictions and binding hashes are in `artifacts/visual-audio-exp011-v1/`; its `preview.html` is the local viewer. Sealed evaluation is in `artifacts/visual-audio-exp011-evaluation-v1/`. Command outputs are retained as `artifacts/visual-audio-*.log`. Raw files and sample-level answers remain excluded from Git.

| Immutable item | SHA-256 |
| --- | --- |
| Registration before real-data computation | `e443c66623ef3d862dc70d5bbaa19f6da39b7ec36af29567cc7282759e8bfe1b` |
| Rendering configuration, canonical JSON | `e3876ee2f46defc9f729ef54ac93c09f977cf7487062ea7a45fef5a533084b9a` |
| Experiment runner | `40eecc8bb960cc8f628d274d36f555a29e9c1d0a7250ac486bb87f5429eb49e6` |
| Renderer/comparison implementation | `5fef9a7978ca5612828f26273e7a2f8ef79fa2db2448cc337a15f90e81952061` |
| Prompt | `612310dc546fd9111e1d8bb217f8738c731b57f13dea42a0357eca6094aee3c5` |
| Published aggregate | `06e1cbc04aed2fd22ea7ad33fc817ce4d553782e5c12a250861fe2b1c94dc1ad` |

The registration was written at 11:03:12 UTC, before source selection/rendering/control execution. Protocol/configuration hashes, predictions and prepared messages were not changed after evaluation. The preview generator and additional infrastructure tests do not change the frozen renderer or experimental runner. Reproducing against new code requires a new preparation directory and registration; old runs are never overwritten.