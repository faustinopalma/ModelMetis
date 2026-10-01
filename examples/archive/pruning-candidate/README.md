# Pruning Comparison

**This page records an exploratory candidate that removed three diagram types.** [Open the comparison](index.html) to inspect all eight primary decisions and both repeats, including the D03 repeat whose answer differs from its identical-request counterpart. The [simple-method comparison](../../audio-comparison/README.md) holds the current configurations.

Correct reference selects the publisher-labeled class; Model choice selects the assigned class. Other disables model choice because no reference was selected, while the arrows still browse references. Excluded-class cases mark the correct reference as withheld. Audio, A/B, enlargement and recorded explanations remain available.

Welch, FFT, spectrogram and cepstrum are displayed, four of the 23 diagram types the model studied after band power, autocorrelation and dominant-frequency tracking were removed. The published figures are full resolution; the model studied them as resized contact-sheet cells.

| Case | Published decision | Significance |
| --- | --- | --- |
| Ottawa D03, repeat | [Wrong C06 assignment](responses/replicate-Ottawa-known-D03-mask111.json) | Correct class is C02; an identical request also returns Other |
| Ottawa D01, healthy | [Correct C01 assignment](responses/regression-Ottawa-known-D01-mask111.json) | Complete-input control falsely rejects it |
| Jin T01, class excluded | [Correct Other response](responses/regression-Jin-excluded-T01-mask111.json) | Correctly rejects when its class is absent |

`inputs/` contains exact text parts and response schemas with original contact-sheet hashes. `responses/` contains exact parsed decisions. [Provenance](provenance.json), [attribution](ATTRIBUTION.md) and the [manifest](manifest.json) bind the release to its sources. Media are stored once by content hash.

Publisher labels are shown with every decision so it can be checked. [Pruning results](../../../docs/DSP_PRUNING_RESULTS.md) own the scientific interpretation.
