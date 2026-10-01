# Triple Removal Helps One Case But Fails The Safety Gate

**Do not adopt the combined removal of dominant-frequency tracking, autocorrelation and band power yet.** The completed 46-decision experiment recovers healthy Ottawa D01 in one primary comparison, but an exact-request repeat misassigns Ottawa D03 to C06 instead of C02. The same triple-removal request also returns Other, exposing decision instability. Single removals and their combinations do not change any of the 32 primary factorial outcomes for D03/D07. These are development data for selection; no pruning policy or clean final evaluation has been executed.

The [frozen strategy](DSP_PRUNING_PROTOCOL.md) separates the current crossed tests from later policy selection and final evaluation. All 46 registered requests completed with HTTP 200, valid binary responses and no retries. Twenty-six focused local tests pass. Historical artifacts and the v14 comparison remain unchanged.

## The Complete Factorial Does Not Recover D03 Or D07

The factorial has three binary removal factors and eight combinations. Each combination is tested on D03 and D07 with the true reference present and excluded: four decisions over two underlying recordings, not four independent acquisitions. Each cell uses a fresh matched control protocol. The table excludes the separately reported exact-request repeats.

| Removed explicit views | Correct known / 2 | Wrong known / 2 | False rejection / 2 | Correct excluded rejection / 2 | Wrong acceptance / 2 |
| --- | --- | --- | --- | --- | --- |
| None, `mask000` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Bands, `mask001` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Autocorrelation, `mask010` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Autocorrelation + bands, `mask011` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Dominant-frequency track, `mask100` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Dominant-frequency track + bands, `mask101` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| Dominant-frequency track + autocorrelation, `mask110` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |
| All three, `mask111` | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 |

Every primary factorial decision is Other. Thus all observed matched single-factor effects on these categorical outcomes are zero, including contrasts conditional on the other two factors. The small sample and single primary completion per cell do not establish that the factors have no influence. In particular, the repeat below contradicts any claim of deterministic safety for triple removal.

The targeted spectral-kurtosis removal also leaves D07 unchanged: a false rejection with the class present and a correct rejection with it excluded. Its earlier error-associated citation therefore does not translate into a recognition improvement in this two-case removal probe.

## Regression Cases Show A Benefit That Is Not Yet Attributable To One Removal

Jin T01 and Ottawa D01 are tested with the complete input and all three primary views removed. Only D01 with the class present changes.

| Case | Required response | Complete input | Triple removal | Measured effect |
| --- | --- | --- | --- | --- |
| Jin T01, class present | C01, excess hall adhesive | C01 | C01 | Correct recognition retained |
| Jin T01, class excluded | Other | Other | Other | Correct rejection retained |
| Ottawa D01, class present | C01, healthy | Other | C01 | False rejection becomes correct recognition |
| Ottawa D01, class excluded | Other | Other | Other | Correct rejection retained |

Combining the four regression cases with the four primary factorial cases gives an eight-case matched comparison: complete input has 5/8 correct decisions, 1/4 correct known recognitions and 3/4 false rejections; triple removal has 6/8 correct decisions, 2/4 correct known recognitions and 2/4 false rejections. Both have 4/4 correct excluded rejections and zero wrong assignments in these primary cells. This aggregate is incomplete as a safety assessment without the repeat evidence.

D01's improvement was observed once, and its six intermediate single/double-removal arms were not part of this fixed acquisition plan. The current data cannot identify which individual removal or interaction caused the improvement. The model attributes the accepted healthy result mainly to PSD-estimator, STFT, reassigned-STFT, wavelet and cepstral numerical controls, despite disagreement from the historical Welch baseline. This rationale is a report of its evidence use, not a proof of internal causal reasoning.

## An Identical Triple-Removal Request Produces An Unsafe Alternative

The four additional calls repeat registered request bytes exactly. The preregistered interleaved ordering means that the replicate block can run before its primary counterpart; primary versus repeat is a design label, not a chronological claim.

| Repeated case | Arm | Primary response | Repeat response | Agreement |
| --- | --- | --- | --- | --- |
| D03, class present | Complete input | Other | Other | Yes |
| D03, class excluded | Complete input | Other | Other | Yes |
| D03, class present | Triple removal | Other | C06, bowed rotor | No; C02 rotor unbalance is required |
| D03, class excluded | Triple removal | Other | Other | Yes |

The two triple-removal D03 known-class responses include one false rejection and one wrong assignment. This is not an estimated 50% production error rate: there are only two completions for one fixed input. It is sufficient to block adoption under the no-observed-safety-regression criterion. The two full-input D03 known responses both reject, so the observed unsafe alternative occurs only in the removed-input pair; a broader causal or frequency claim requires more repetitions.

The wrong response selects C06 using the nearest Welch baseline, harmonic-family alignment and cyclic evidence, while explicitly acknowledging a different dominant FFT line, carrier-band modulation and impulsiveness. This illustrates why error attribution is an intervention shortlist rather than an automatic deletion rule: some views associated with a false rejection may also discourage a worse wrong acceptance. The user's ordering of errors remains decisive: wrong assignments are unacceptable; unnecessary human review is a secondary cost.

## The Intervention Removes Presentation Channels Without Replacing Them

Each arm removes the selected image cells, corresponding original and extension measurements, per-view distances, guide entries and allowed view citations. Retained image position, dimensions, detail setting and pixels are fixed. The original reference bank, label mapping and order are unchanged within each matched case. No previous model survey, explanation or outcome is supplied.

The actual-request audit verifies 9,196 retained image cells with identical pixels, 554 removed cells fully blank, and all 2,979 emitted comparison citations present in the supplied request. All 46 requests pass explicit numeric/guide/channel-removal checks. The removal is therefore not merely cosmetic, and observed invariance is not explained by accidentally leaving the same named measurement in the text.

Other representations still encode related physical information. Removing the dominant-frequency track leaves FFT peaks and STFT structure; removing band-power tables leaves spectra. Several removed-input responses continue to reject using these retained views. This is evidence of presentation redundancy on the tested cases, not proof that the underlying spectral mismatch stopped influencing the model.

## Use These Data To Narrow Selection Before Opening Final Results

The present decision is to retain the unpruned policy as the comparison baseline and not promote the triple-removal policy. Individual removals remain candidates for simplifying the input, but no known-class recognition gain is demonstrated for D03/D07. The spectral-kurtosis probe provides no observed benefit for D07. Preserve the healthy D01 gain as a lead to investigate rather than generalizing it to other conditions.

A proposed development follow-up is to complete the six missing D01 single/double-removal arms in both known and excluded conditions, then repeat the smallest beneficial candidate against the full control on D03 and D07. This follow-up is not registered or executed here. It should determine whether a smaller removal retains the D01 benefit without reproducing the unsafe D03 assignment. If no candidate clears that criterion, do not prune merely because a view appeared in an erroneous explanation.

Only after choosing a policy should its retained views, model settings, prompt, reference bank and acceptance criteria be frozen for clean final testing. All four recordings in this experiment and their sibling acquisition windows remain development data. All Jin source acquisitions and Ottawa profile 8 already have exposure; they cannot be relabeled clean. Candidate unused Ottawa acquisitions require an exposure-ledger audit before final selection. No final signals or final outcomes were opened during this experiment, and no final dataset is claimed to have been certified untouched.

## Reproduce The Comparison From Immutable Evidence

The [public registration extract](../examples/results/pruning-registration.json) contains all 46 planned cells, 42 unique requests, four exact-byte repeat relationships, source hashes and the frozen implementation hashes, without authorization or spending metadata. The [paired results](../examples/results/pruning-summary.json), [per-request outcomes](../examples/results/pruning-decisions.json) and [input audit](../examples/results/pruning-input-audit.json) retain the comparison and validation evidence. The [unsafe decision](../examples/audio-comparison/responses/replicate-Ottawa-known-D03-mask111.json) and [recovered healthy decision](../examples/audio-comparison/responses/regression-Ottawa-known-D01-mask111.json) preserve the exact parsed model content and original response hashes; raw HTTP envelopes remain local.

The deployment remains `gpt-5.6-sol`, version `2026-07-09`, `DataZoneStandard` capacity 100, `reasoning_effort=low`, with 8,192 maximum completion tokens in every arm. No cloud infrastructure was modified. Usage is 3,239,902 prompt tokens and 104,626 completion tokens. Four short-context calls have a combined estimate of USD 0.8935652; forty-two exceed the existing pricing guard and remain unpriced. This is not the total experiment cost.

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_pruning_experiment evaluate --output outputs/dsp-pruning-cross-v1
.\.venv\Scripts\python.exe -m pytest -q tests/test_dsp_extensions.py tests/test_audio_comparison.py
```

Evaluation validates source-bound inputs, actual response bytes, comparison citations and sealed truth without invoking the model. Re-executing the run command skips completed attempts; it cannot overwrite or silently replay a registered request. The completed acquisition is exploratory and does not establish independent-machine or unseen-fault generalization.
