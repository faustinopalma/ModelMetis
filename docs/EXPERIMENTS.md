# Experiment History

**The tested teacher-to-specialist approach has not produced useful diagnostic performance.** Jin spectral controls and frozen encoders separate a small development split, but cross-drone classification and grouping remain poor. DSP-to-Sol rejected every known-condition trial. No model passed an operational promotion gate.

## Evidence Rules

The [data boundaries](CONTEXT.md#data-boundaries) apply to every experiment. Operational specialists learn from teacher silver labels; supervised controls and publisher-derived support examples have separate provenance. Development results are exploratory. Ottawa's final set and Jin/B development recordings are consumed evidence; repartitioning them does not create fresh confirmation data. Drone C remains unevaluated by models.

Frozen local registrations and machine-readable reports retain execution timestamps, configurations, hashes, model revisions, dependencies, seeds, failures and accounting. Raw audio, sample-level predictions, publisher references and source mappings stay outside Git. Software checks validate implementation contracts; diagnostic claims require independently scored predictions.

## Attempt Index

| ID | Hypothesis | Executed scope | Outcome |
| --- | --- | --- | --- |
| EXP-001A | Literal category text separates Ottawa conditions | 16 CLAP development queries | 2/16 correct, macro-F1 0.027778; every prediction bowed rotor |
| EXP-001B | Acoustic descriptions improve CLAP | Same 16 queries | 2/16, macro-F1 0.038462; selected by macro-F1 |
| EXP-001 | CLAP silver labels train a useful specialist | 96 labels, fit, 16 final queries | Teacher 1/16, specialist 2/16 |
| EXP-002 | Generative audio improves on CLAP | Four synthetic setup attempts, two Ottawa screens | Direct 2/16; evidence 1/16; collection blocked |
| EXP-003 | Motor context and acoustic measurements improve diagnosis | Two Ottawa screens | Both 2/16, all predictions healthy; collection blocked |
| EXP-004 | Combustion-engine audio is more suitable | Source audit, two partial failed attempts, two screens, 11 silver labels and learning curve | Teacher 3/8; specialists 2/8 and 1/8 |
| EXP-005 | DC removal and normalization help | Eight AI Mechanic queries | 3/8, no macro-F1 improvement |
| EXP-006 | One audio example per category helps | Four supports, eight AI Mechanic queries | 3/8; lower macro-F1 and 3.93 times baseline cost |
| EXP-007 | Jin conditions are acoustically separable | Four supervised controls and twelve teacher queries | Spectral controls 12/12; GPT Audio 6/12 |
| EXP-008 | Frozen encoders improve one-shot classification | Three encoders and fixed mixture; two technical blocks recorded | Each completed candidate 12/12, tying the spectral control |
| EXP-009 | Sparse references transfer between drones | Nine supports, 54 queries, fixed classifiers/rejection rules | Forced classification 4-9/54; each geometric policy abstained on 54/54 |
| EXP-010 | Larger encoders improve condition similarity | Five encoders, fixed retrieval and clustering | Dasheng P@5 27.41%; cluster pair precision 11.98% |
| EXP-011 | STFT images support open-set comparison | Offline renderer and numerical control; visual inference not executed | Control abstained on 12/12 |
| EXP-012 | DSP measurements and images support Sol comparison | One synthetic gate and twelve real trials | Known recognition 0/9; false rejection 9/9; unknown rejection 3/3 |

## EXP-010: Similarity Geometry And Larger Encoders

The [protocol](EMBEDDING_SIMILARITY.md) tests label-blind retrieval and clustering on the unchanged nine A supports and 54 B queries. Each B query retrieves other B recordings by cosine similarity, excluding itself. Random same-condition P@5 is 5/53 = 9.43%; random same-maneuver agreement is 8/53 = 15.09%. Pairwise AUC measures similarity ranking, with dependent pairs.

| Encoder | Stored tensor scalars | Same-condition P@1 | Same-condition P@5 | Condition pair AUC | Same-maneuver P@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| FISHER-small | 21,393,408 | 20.37% | 20.00% | 0.587877 | 11.11% |
| ECHO-small | 21,540,096 | 29.63% | 18.52% | 0.616930 | 15.19% |
| EAT-base30 | 89,972,736 | 29.63% | 20.74% | 0.614049 | 11.11% |
| EAT-large20 | 308,867,072 | 25.93% | 19.63% | 0.633202 | 13.70% |
| Dasheng-1.2B | 1,134,047,488 | 33.33% | 27.41% | 0.723365 | 13.70% |

Dasheng yields 18/54 correct first neighbors and 74/270 correct top-five links. Architecture, pretraining corpus and training duration differ between candidates, so this comparison does not isolate parameter count.

HDBSCAN uses fixed `min_cluster_size=5`, `min_samples=3` and normalized Euclidean distance. FISHER/ECHO leave all queries unassigned. EAT-base produces groups of 7 and 11 with 13/76 matching-condition pairs; EAT-large groups of 18 and 5 with 23/163; Dasheng groups of 39 and 5 with 90/751. These groups do not support representative-label propagation. In combined A/B retrieval, B-neighbor P@5 is 91.85-99.63% against an 85.48% random baseline, showing strong device-associated structure.

EAT-large uses `worstchan/EAT-large_epoch20_pretrain@1109aaae544915a2b82182c643c1894b1b4d9f27`; Dasheng uses `mispeech/dasheng-1.2B@e830b3b0014affc8447a9c15d18bb196a747137f`. Both loaded exactly. Eight metadata/download/probe/extraction workers completed below 600 seconds each, without retries. Synthetic probes required repeatable finite nonzero vectors. Real extraction took 340.795 s and 66.034 s; median query times were 4.999 s and 0.576 s. CPU float32, four Torch threads and x64 emulation were used; these are single-run timings. Dasheng's published pretraining uses general audio, not an industrial-fault-specific corpus.

Two guessed repository addresses returned HTTP 401 before official links resolved them; neither was a model-access failure. The aggregate (`ml/embedding-geometry-v1.json`; local-only) retains all five results, eight workers, hashes and runtime details. Independent recomputation matched 1,620 top-k checks, ten pair-AUC values and ten cluster-pair counts. No fitting, extra labels, C inference or cloud compute occurred. Retrieval improved, but reliable grouping and cross-machine invariance remain unestablished.

## EXP-009: Cross-Drone One-Shot And Abstention

The [registered protocol](ADAPTIVE_MODELS.md#exp-009-cross-drone-sparse-reference-test) selected the lowest decoded-PCM hash per condition from A and per condition/maneuver cell from B. Eligibility required complete labeled microphone pairs; only microphone 1 was exported. Nine conditions and six maneuvers yield nine supports and 54 queries. Each whole drone is one physical group. Audio is 8,000 samples, mono 16 kHz PCM16, DC-centered and peak-scaled to 0.95. Query labels and source metadata remain sealed.

| Method | Correct / 54 | Macro-F1 | Median query seconds |
| --- | ---: | ---: | ---: |
| Welch/logistic | 7 | 0.098045 | 0.010114 |
| FISHER-small | 4 | 0.049182 | 0.054566 |
| ECHO-small | 9 | 0.095624 | 0.058534 |
| EAT-base30 | 7 | 0.101984 | 1.920413 |
| Uniform three-encoder mixture | 4 | 0.053030 | 2.023969 |

Forced classifiers accepted 54/54; a constant-class baseline scores 6/54. Every encoder and the mixture missed all six healthy queries. Each support-only geometric policy accepted a query only inside half the nearest inter-prototype distance. All three abstained on 54/54: zero coverage, undefined accepted error and 54 potential reviews. Every query has a known condition, so unknown-fault detection was not tested. Independent recomputation matched all 162 encoder labels and distances; minimum distance/radius ratios exceeded 1.59, excluding rounding as the rejection cause.

Two synthetic campaigns completed all four candidates; the second bound the final runner hash. All four real workers completed without failure, timeout or short-input repair. The campaign took 194.439 s. The aggregate (`ml/drone-one-shot-v1.json`; local-only) preserves attempts, forced/selective outcomes, timings, hashes, recalls and confusion matrices.

Models received nine simulated-human support labels. Curation used the full publisher inventory, and evaluation used 54 B labels; query labels used for fitting were zero. Actual human diagnoses and added gold reviews were zero. One held-out drone, unknown original-take lineage and simultaneous changes in dataset/duration limit generalization. No threshold tuning, extra supports, silver collection or C inference followed.

## EXP-008: Frozen Encoders And Uniform Mixture

FISHER-small, ECHO-small and EAT-base30 each scored 12/12 on Jin with four support labels and cosine-centroid classification. Their fixed equal-weight mixture also scored 12/12, tying the spectral control and exceeding GPT Audio's 6/12. The mixture added cost without improving accuracy. The twelve windows come from four previously examined query acquisitions with unresolved motor/session independence and encoding confounds.

BEATs Iter3 official weights returned HTTP 403; no mirror was substituted. EAT's first worker failed before inference because Transformers omitted a nested source module from its cache. Strict loading of the same pinned local package succeeded on the second attempt. A preliminary two-member mixture was retained without evaluation; the final three-member mixture was fixed before sealed evaluation.

The [protocol](ADAPTIVE_MODELS.md#exp-008-frozen-encoders-and-one-shot-classification) and aggregate (`ml/encoder-jin-v1.json`; local-only) retain preprocessing, revisions, runtime, failed attempts and metrics. Execution used local CPU, with no paid calls, cloud resources, online learning or promotion.

## EXP-001: CLAP Distillation Baseline

Ottawa UOEMD-VAFCVS v2 supplies 128 ten-second microphone acquisitions. The split uses speed profile 1 for 16 development recordings, profiles 2-7 for 96 training recordings and profile 8 for 16 final recordings, with both loads represented. Physical motors recur across partitions.

Two [prompts](../configs/audio-prompts.json) scored 2/16 in development. Macro-F1 selected `acoustic` (0.038462 versus 0.027778) before collection. CLAP revision `8fa0f1c6d0433df6e97c127f64b2a1d6c0dcda8a` produced 96 silver labels: 48 healthy, 39 broken rotor bars and nine bowed rotor. Five categories were absent. A specialist fitted 48 log-spectral bands, StandardScaler and logistic regression with `max_iter=1000`, seed 17, using only those silver targets.

| Measurement | Teacher | Specialist |
| --- | ---: | ---: |
| Final correct | 1/16 | 2/16 |
| Final macro-F1 | 0.015625 | 0.059524 |
| Accepted | 16/16 | 16/16 |
| Median inference | 1.318625 s | 0.080191 s |
| p95 inference | 3.127117 s | 0.100963 s |

Teacher/student agreement was 12/16 despite poor correctness. The specialist matched the constant-class baseline. Collection took 156.782594 s plus 14.789293 s loading; training/artifact writing took 13.074640 s. All execution used local x64 CPU on Windows ARM64.

Technical failures included unavailable ARM64 PyTorch wheels and a direct PyPI TLS failure. The separate x64 environment and configured package proxy resolved them without disabling TLS validation. Transformers fetched a safetensors conversion at another revision; all 447 tensors and dtypes matched the original weights. The processor argument changed from `audios` to `audio` before the second development run. The final set is consumed; no model was promoted.

Evidence: [audit](../ml/ottawa-v1-audit.json), [development](../ml/ottawa-v1-development.json), [training](../ml/ottawa-v1-training.json), [final metrics](../ml/ottawa-v1-final.json) and [reproduction](../ml/README.md).

## EXP-002: Generative Audio Teacher

Hypothesis: GPT Audio produces better provisional labels than CLAP. Two fixed prompts, [direct and evidence](../configs/audio-llm-prompts.json), used the same 16 Ottawa development recordings. Selection used eight-class macro-F1, counting abstentions as wrong and retaining candidate order on ties. Collection required multiple accepted classes; planned specialist snapshots were 16/32/64/96 arrivals in seed-17 order.

Qwen audio candidates were inspected but not loaded because of limited local memory headroom; this was not a measured OOM. GPT Audio 1.5 `2026-02-23` was deployed in Sweden Central, GlobalStandard capacity 100, NoAutoUpgrade, Entra-only authentication and default-deny networking. Endpoint details are in [infra](../infra/README.md).

### Live Capability Attempts

| Attempt | Result | Resolution |
| --- | --- | --- |
| probe-01 | Token acquisition failed before HTTP | Verify tenant separately; use subscription-only AzureCliCredential |
| probe-02 | HTTP 200, response model-version check failed | Retain failure and inspect safe identity metadata |
| probe-03 | HTTP 200 returned bare `gpt-audio-1.5` | Require ARM verification of fixed version and upgrade policy |
| probe-04 | Two valid, correct synthetic responses | Tone/noise transport gate passed |

The exercised token audience was `https://ai.azure.com/.default`, API `2025-01-01-preview`, temperature zero, text-only output and 1024 output tokens. The adapter rejects invalid JSON, unknown labels, scores and incomplete responses; it performs no automatic retries. ARM64 Azure Identity installation failed on a native cryptography dependency; the separate x64 environment succeeded.

### EXP-002 Development Result

| Candidate | Correct | Macro-F1 | Accepted | Emitted classes | Median / p95 seconds |
| --- | ---: | ---: | ---: | --- | ---: |
| direct-v1 | 2/16 | 0.029412 | 16/16 | 15 faulty_bearing, 1 rotor_unbalance | 4.507 / 4.866 |
| evidence-v1 | 1/16 | 0.035714 | 5/16 | 5 faulty_bearing; 11 abstentions | 4.310 / 4.625 |

Both screens completed without transport/schema errors. The selected evidence prompt supplied one class; collection and snapshots were blocked. No new final-test access occurred. Exact prompts, predictions, attempts and usage are retained in the [cumulative aggregate](../ml/audio-experiments-20260918-jin.json) and local `artifacts/ottawa-v2`.

## EXP-003: Context And Audio-Derived Measurements

The [fixed prompts](../configs/audio-llm-prompts-v2.json) test induction-motor context with and without deterministic spectral measurements. `spectral-v2` adds Welch peaks, relative levels, band energy, centroid, flatness, crest factor and excess kurtosis. Neither prompt receives RPM, source identity or query labels. Both use genuine audio and the same 16 development queries.

Both completed 16/16 and predicted healthy for every recording: 2/16 correct, macro-F1 0.027778, healthy recall 1 and every fault recall 0. Median inference was 4.586 s for context and 4.850 s for spectral. The tie rule selected context; one-class output blocked collection and snapshots. The separate ledger and local `artifacts/ottawa-v3` preserve the run. The original hypothesis that bench sound caused bearing predictions remains unproven.

## EXP-004: Combustion-Engine Transfer Experiment

AI Mechanic v1 contains recordings of one BMW M54b25, under Apache-2.0. Fifteen of 34 publisher-training recordings were identical constant PCM -8 with contradictory labels. The importer first stopped on duplication/conflicts; a label-independent constant-signal gate excluded these files. Nineteen usable acquisitions remained: normal 6, air leak 4, oil cap open 4 and background noise 5. The two lowest source hashes per class supplied eight development recordings; eleven remained for training. Each input uses its first ten seconds or its shorter full duration. Publisher testing audio was not used; session independence is unknown.

### Transport Contract Amendment

The first direct-v1 attempt failed on its first HTTP-200 response. A second unchanged-prompt attempt accepted three responses, then failed on non-JSON output. All five requests remain in the ledger; differential-v1 was not called. [Version 2](../configs/mechanic-audio-prompts-v2.json) moved instructions, taxonomy and a JSON shape into the system message. The parser remained strict; the waveform and diagnostic instructions were unchanged.

### Result And Learning Curve

Both v2 screens returned eight valid answers. Direct scored 3/8, macro-F1 0.277778, with normal recall 1 and air-leak recall 0.5. Differential scored 2/8, macro-F1 0.111111, recognizing only background. The fixed rule selected direct, which produced eleven training labels: ten normal and one background.

| Observed arrivals | Training outcome | Development correct | Macro-F1 |
| --- | --- | ---: | ---: |
| 4 | Blocked: one accepted class | Not evaluated | Not applicable |
| 8 | Fitted from seven normal and one background silver labels | 2/8 | 0.111111 |
| 11 | Fitted from all eleven silver labels | 1/8 | 0.062500 |

Median specialist inference was 0.034568 s and 0.035917 s. The ledger recorded 32 requests and USD 0.138665 estimated consumption, including failed attempts. No useful learning improvement was established. [Curve implementation](../scripts/learning_curve.py) and local `artifacts/mechanic-v1` retain stage separation and checkpoints.

## EXP-005: Signal Level Control

Five masked recordings had AC RMS below -40 dBFS. [The normalized variant](../configs/mechanic-audio-prompts-v3.json) removed DC and applied one linear gain to a 0.95 peak, preserving the diagnostic wording and recording original/transmitted hashes. No denoising or source-aware processing was added.

All eight queries returned valid answers: 3/8 correct, macro-F1 0.277778, tied with direct-v2. Normal recall was 1, background 0.5 and both fault recalls 0. The frozen tie rule retained direct-v2. Normalized collection and another learning curve were blocked.

## EXP-006: One Audio Example Per Category

Hypothesis: explicit audio/label examples improve GPT Audio on AI Mechanic. The lowest canonical-audio hash per class selected four supports from the eleven training acquisitions, leaving seven unlabeled training inputs and the unchanged eight development inputs. Publisher annotations use `simulated_human_from_publisher` provenance. ID, group and audio overlap are rejected before network access.

The [one-shot prompt](../configs/mechanic-audio-prompts-v4.json) preserves direct-v2 settings and adds four audio/label demonstration pairs. Ordered support hashes and labels are bound into the prompt hash. The run was limited to eight requests, no retries or support reselection. Improvement required higher accuracy and macro-F1 without lower coverage.

| Measurement | Zero-shot direct-v2 | One-shot |
| --- | ---: | ---: |
| Correct | 3/8 | 3/8 |
| Macro-F1 | 0.277778 | 0.271429 |
| Accepted | 8/8 | 8/8 |
| Air-leak recall | 50% | 100% |
| Background recall | 0% | 0% |
| Normal recall | 100% | 50% |
| Oil-cap recall | 0% | 0% |
| Median inference | 4.325054 s | 9.525606 s |
| Estimated inference cost | USD 0.03557 | USD 0.13989 |

All eight calls succeeded without retries. One-shot used 7,160 prompt tokens, including 4,000 audio tokens, and 399 completion tokens. Cost was 3.932809 times baseline, excluding simulated human annotation effort. The gate failed; the ledger is exhausted. No new silver, fitting or support expansion followed. [Aggregate](../ml/audio-experiments-20260918-one-shot.json).

## EXP-007: New Motor Data With Supervised Diagnostic Controls

Jin v1 supplies twelve PCB-microphone recordings, four classes and three directions. Publisher hashes were verified. Files are mono 44.1 kHz, about 600 seconds each; healthy files use PCM16 and faults FLOAT, an acquisition confound. Physical-unit/session independence is undocumented.

Front recordings supply one ten-second support per class; left recordings supply 30 nonoverlapping ten-second training windows per class; right recordings supply queries at offsets 0, 120 and 240 seconds. Totals are four supports, 120 training windows and twelve queries from four recordings per role. DC removal and peak scaling to 0.95 precede PCM16 export. This is direction transfer, with no independent final set.

Fixed supervised controls use either 48-band log-Welch/StandardScaler/logistic regression (`max_iter=1000`, seed 17) or 20 MFCCs with first/second deltas and temporal mean/std, StandardScaler and RBF SVM (`C=10`, `gamma=scale`, balanced weights). MFCC extraction uses 16 kHz, FFT 1024, hop 512 and 64 Mel bins. Each fits once on four supports and once on 120 training windows. Controls have separate non-operational lineage.

GPT Audio receives the same four supports, with [fixed Jin prompts](../configs/jin-audio-prompts.json), at most twelve requests and no retries. The exploratory threshold requires accuracy >=0.75, macro-F1 >=0.70 and recall >=2/3 per class.

| Method and labeled input | Correct | Macro-F1 | Recall: adhesive / healthy / magnet / bearing | Median inference |
| --- | ---: | ---: | --- | ---: |
| Welch/logistic, four supports | 12/12 | 1.000000 | 1 / 1 / 1 / 1 | 0.039365 s |
| Welch/logistic, 120 training windows | 12/12 | 1.000000 | 1 / 1 / 1 / 1 | 0.042603 s |
| MFCC/SVM, four supports | 6/12 | 0.446429 | 1 / 0 / 1/3 / 2/3 | 0.130847 s |
| MFCC/SVM, 120 training windows | 8/12 | 0.589286 | 0 / 2/3 / 1 / 1 | 0.191704 s |
| GPT Audio, four supports | 6/12 | 0.375000 | 1 / 0 / 1 / 0 | 8.550382 s |

All methods accepted 12/12. GPT Audio predicted magnet for every healthy and tight-bearing query, failing the threshold. Its twelve calls cost an estimated USD 0.21281. The spectral controls show separability under this split, with unresolved acquisition confounds. The two training regimes also change direction, so their difference is not a controlled label-count curve. MFCC timings include lazy imports/JIT; the control report's zero load time is an unmeasured placeholder. [Exact aggregate](../ml/jin-directions-v1.json).

## EXP-011 And EXP-012: Visual Comparison

[EXP-011](VISUAL_AUDIO_EXPERIMENT.md) froze an STFT-only reference comparison. Its numerical control abstained on all twelve trials; no multimodal inference ran because the target deployment was unavailable. [Results](VISUAL_AUDIO_RESULTS.md).

[EXP-012](DSP_LLM_PROTOCOL.md) supplied typed DSP measurements and original FFT/STFT images to pinned GPT-5.6 Sol. One synthetic gate and twelve real requests completed without inference failures or retries. All real outcomes were outside-reference: 9/9 known cases wrongly rejected and 3/3 unknown cases correctly rejected. The trials reuse three query clips. Total estimated consumption including the gate was USD 0.72875088. [Results, cost and provenance](DSP_LLM_RESULTS.md).

## Accounting

| Audio aggregate | Attempts | Reserved requests | Responses with known usage | Estimated consumption | Conservative accounting |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Through EXP-005](../ml/audio-experiments-20260918.json) | 14 | 109 | 108 | USD 0.5014325 | USD 4.6114325 |
| [Through EXP-006](../ml/audio-experiments-20260918-one-shot.json) | 15 | 117 | 116 | USD 0.6413225 | USD 4.7513225 |
| [Through EXP-007](../ml/audio-experiments-20260918-jin.json) | 16 | 129 | 128 | USD 0.8541325 | USD 4.9641325 |

The difference is a retained USD 4.11 reservation for the initial pre-HTTP failure, not additional measured spending. Reservations use a conservative input/output token bound; valid usage releases the difference, while missing usage retains it. Shared ledger limits cannot be raised or bypassed by recreating the ledger. The audio worker's scheduling deadline is not an OS-enforced hard kill. Reports reconcile nonempty predictions and all ledger attempts. Prices are list-price estimates; local hardware, electricity and labor are unmeasured. DSP-to-Sol accounting is separate. No AML/GPU execution or shutdown was tested.
