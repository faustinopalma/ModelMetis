# Archived Pruning Candidate Review

**This is an archived later variant, not the current method, and the triple-pruned candidate is not approved.** [Open the comparison](index.html) to inspect all eight primary decisions and both repeats. The unsafe D03 repeat and disagreement with its identical-request counterpart remain visible. The [current simple-method comparison](../../audio-comparison/README.md) uses a different input and configuration.

Correct reference selects the publisher-labeled class; Model choice selects the assigned class. Other disables model choice because no reference was selected, while the arrows still browse references. Excluded-class cases mark the correct reference as withheld. Audio, A/B, enlargement and recorded explanations remain available.

Only Welch, FFT, spectrogram and cepstrum are displayed. The model received 23 retained types after removing band power, autocorrelation and dominant-frequency tracking. This display is not another inference experiment. Full-resolution published figures differ from the declared resized contact sheets used by the model.

| Case | Published decision | Significance |
| --- | --- | --- |
| Ottawa D03, repeat | [Wrong C06 assignment](responses/replicate-Ottawa-known-D03-mask111.json) | Correct class is C02; an identical request also returns Other |
| Ottawa D01, healthy | [Correct C01 assignment](responses/regression-Ottawa-known-D01-mask111.json) | Complete-input control falsely rejects it |
| Jin T01, class excluded | [Correct Other response](responses/regression-Jin-excluded-T01-mask111.json) | Correctly rejects when its class is absent |

`inputs/` contains exact text parts and response schemas with original contact-sheet hashes. `responses/` contains exact parsed decisions without provider transport metadata. [Provenance](provenance.json), [attribution](ATTRIBUTION.md) and the [manifest](manifest.json) bind the release to its sources. Media are stored once by content hash.

Labels are deliberately visible. This is not a blinded human test or a clean final evaluation set. [Pruning results](../../../docs/DSP_PRUNING_RESULTS.md) own the scientific interpretation.
