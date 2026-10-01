# Test Class Memory On Whole Ottawa Acquisitions

**Prepare a paired fixed-memory versus adaptive-memory pilot on Ottawa only.** Both arms start from three complete acquisitions per class, inspect identical compact class cards, and can retrieve previously labeled reports before requesting simulated human review. The adaptive arm incorporates reviewed cases for subsequent decisions; the fixed arm never updates its references. Preparation and synthetic tests make no model calls, and reserved evaluation remains locked.

## Freeze Acquisitions Before Building Reports

Use the audited microphone-only Ottawa v2 inventory: eight classes, eight operating profiles and two load states, totaling 128 whole ten-second acquisitions. The class mapping remains the publisher mapping used by the existing importer. CSV/MAT copies, channels, windows and augmentations of one acquisition cannot cross roles. Every acquisition ID, original group and canonical exported WAV hash must be unique. Jin is excluded; dividing its recordings into additional windows does not provide independent cases for this pilot.

| Role | Selection within every class | Per class | Total |
| --- | --- | --- | --- |
| Initial references | Profile 1 unloaded, profile 2 loaded, profile 8 unloaded | 3 | 24 |
| Reserved comparison | Complete profiles 5 and 7, both load states | 4 | 32 |
| Enrichment stream | Remaining acquisitions | 9 | 72 |

These cells are fixed before report generation or model outcomes: seeds cover two constant profiles and one decreasing profile; reserved profiles include one increasing and one decreasing profile. Profile numbers are acquisition context, not independently measured shaft RPM. Opaque acquisition IDs derive from audited audio hashes rather than fault-coded filenames. The stream order is the SHA-256 order of those IDs under the fixed experiment namespace, independent of model outcomes. Both arms use exactly that order, with no reshuffling after results.

This partition is acquisition-disjoint and keeps entire reserved profiles out of development. It is not machine-disjoint: the same physical motors recur. Prior project exposure has not been cleared, including previously consumed profile 8, so the reserved set is not certified as a fresh benchmark. A separate exposure audit and explicit release gate are required before any final inference. Preparation reads inventory metadata for all roles but computes signals and cards only for the 24 seeds. The first `next` command computes only the current stream query.

## Use Compact Cards Without Inventing A Typical Recording

The four supplied views are centered full-band Welch PSD, FFT detail at 0-500 Hz, full-band STFT on a logarithmic frequency axis, and real cepstrum to 0.1 seconds. DSP calculations reuse the existing implementation on the complete 420,000-sample acquisition; they do not create independently scored windows. Welch uses the established 1,024-sample Hann frame and 256-sample hop. Cepstrum uses the existing extension defaults. Existing source peak normalization and the lack of calibrated sound pressure remain explicit limitations.

Each class card overlays all admitted individual spectral and cepstral curves, labels their observed profile/load context, and shows the STFT of a real reference minimizing average Welch distance to the other class members. It also records the observed pairwise distance minimum, median and maximum. These are descriptive sample statistics, not confidence intervals, acceptance thresholds or evidence that three examples cover the entire class. Missing regimes are not synthesized. Card updates remain deterministic; no additional LLM is asked to invent a narrative class rule.

Images are 1,760 by 1,100 pixels, with fixed panel positions, frequency domains and FFT/STFT intensity limits. Card and source hashes, software versions, policy and implementation are registered. Numeric nearest-class Welch distances are uncalibrated retrieval aids. They do not independently accept or reject a query. This four-view memory input is a new experiment, not the previously unapproved 23-view pruning candidate, and its result cannot isolate a pruning effect.

## Review Only After Recording The Model Decision

1. Supply the unknown query report and all eight class cards. Allow only `accept(condition_id)` or `review`; require actual query and class citations and a concise observable explanation. Model confidence is not treated as a calibrated probability.
2. On review, retrieve at most two already labeled examples from each of at most two candidate classes. Rank only current bank members using the existing centered-Welch distance. If the model names no candidates, use the two closest bank classes as retrieval candidates, without forcing acceptance. Retain all eight cards so retrieval does not silently redefine the taxonomy.
3. Record a second decision from a fresh request containing the cards, retrieved reports and query. Do not feed an earlier model explanation back as evidence. An accepted decision closes the case without revealing its publisher label to the learner.
4. Only an unresolved second decision can access the publisher-label oracle. Both arms have at most 16 simulated reviews, counted independently. The frozen arm records the review without changing its bank. The adaptive arm adds the confirmed acquisition and creates a new memory version for subsequent cases. Initial labels plus reviews are at most 40 per arm; the adaptive bank contains at most 40 references.
5. Preserve first and second decisions, raw responses, request hashes, bank version and each immutable state transition. A reviewed case stays review-required in automatic-recognition metrics. Budget-exhausted cases remain unresolved rather than being automatically relabeled or forced into a known class. Technical or schema failures stop the transition and cannot consume an oracle label.

The oracle simulates a correct human answer using publisher annotations. It measures intervention counts, not real human accuracy or annotation time. This pilot starts with all eight classes represented; new-class discovery and excluded-class rejection are separate, unmeasured questions. Confident wrong assignments do not trigger review and must remain visible to the evaluator. Human labels are gold additions; model predictions never become reference labels.

## Compare Automatic Decisions Before Scoring Human Corrections

The primary comparison is wrong automatic assignments and correct automatic recognitions on the same 72 stream acquisitions. Report automatic coverage, review-required cases, reviews actually consumed, labels revealed, memory size, request count and uncertainty from the small acquisition count. Do not count two stages as two independent cases, or relabel a human-corrected example as an automatic success. More correct recognitions at no additional wrong assignments is promising; rejecting almost everything is not. Any observed increase in wrong assignments blocks promotion pending investigation.

After both streams finish, compute development metrics once against sealed truth. The 32 reserved acquisitions remain inaccessible to the runner. Final evaluation needs a separate frozen release of the two terminal memory states and an explicit authorization; no policy, views or thresholds may be selected from final outcomes. No operational safety or state-of-the-art claim follows from this small pilot. External published scores remain reference points; retraining external models is outside scope.

## Prepare And Inspect Without Inference

```powershell
.\.venv\Scripts\python.exe -m scripts.dsp_memory_experiment prepare --output outputs/dsp-memory-ottawa-v1
.\.venv\Scripts\python.exe -m scripts.dsp_memory_experiment status --output outputs/dsp-memory-ottawa-v1
.\.venv\Scripts\python.exe -m scripts.dsp_memory_experiment next --output outputs/dsp-memory-ottawa-v1 --arm fixed
.\.venv\Scripts\python.exe -m scripts.dsp_memory_experiment next --output outputs/dsp-memory-ottawa-v1 --arm adaptive
.\.venv\Scripts\python.exe -m pytest tests/test_dsp.py -k memory -q
```

Use a new output path for every implementation or protocol change. `prepare` refuses overwrite; `next` returns the same bound pending request on repetition. Initial requests from the two arms should be byte-identical. Requests use the existing `modelmetis-dsp-sol` selector, expect `gpt-5.6-sol-2026-07-09`, and retain low reasoning effort with an 8,192-token completion limit. The registered maximum stream budget is 288 model requests: 72 acquisitions times two arms times at most two stages. This is a bound, not an executed campaign or automatic paid authorization. There is no HTTP sender or cloud-resource operation in this preparation tool.

`submit --arm fixed|adaptive --response PATH` validates a supplied original model-response JSON against the pending request contract, expected model and complete finish status. `review --arm fixed|adaptive` consumes only an eligible pending oracle intervention. `evaluate-stream` refuses to expose metrics until both streams are complete. Supplied responses are marked as externally supplied with transport binding not independently verified; before an automated paid run, bind these actions to the existing immutable HTTP runner and verify the live deployment. Never present synthetic fixtures or manually supplied content as measured model performance.

The sealed directories and allowlisted request builder prevent accidental label leakage; they are not an operating-system sandbox. Complete records, truth, requests and responses stay under ignored local outputs. Public examples and prior experimental artifacts remain unchanged.
