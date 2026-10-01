# Simple Method Comparison

**[Open the comparison](index.html) to listen to each recording beside its references and inspect the recorded model decision.** It contains all 48 decisions of three separately reported configurations. Select a collection; never pool their counts.

| Collection | Configuration | Decisions |
| --- | --- | --- |
| Jin: reports + distances | B, reports plus Welch spectral distances | 12 reserved right-microphone windows and 4 excluded-class tests |
| Ottawa: reports only | A, reports without distances | 16 profile-2 development acquisitions |
| Jin: calibrated replay | C, calibrated distance rule, exploratory | The same 16 Jin inputs, decided after inspecting configuration B |

The input recording is on the left with its publisher class. A reference is on the right: Correct reference shows the publisher class, Model choice shows the class the model selected, and the arrows browse every reference. A reference marked withheld was removed from that request, so the expected answer is different. The note under each outcome gives the Welch distances supplied to the model, or for configuration A the recorded numerical control that the model did not receive.

The model received each report's eight figures as resized contact-sheet cells together with its numerical measurements; it never received audio. The page shows those figures at full resolution and plays the original ten-second excerpts. Link to a single decision with `index.html#<case-id>`, for example `index.html#jin-distances-excluded-T04`.

| Folder or file | Contents |
| --- | --- |
| `inputs/` | Exact transmitted text and response schema; each image part is replaced by its contact-sheet hash and cell list |
| `responses/` | Exact parsed decisions and original request/response hashes, without transport metadata |
| `media/` | Content-addressed original WAV excerpts and full-resolution DSP figures |
| [provenance.json](provenance.json) | Per-record collection, class, audio hash, rate, duration and figure hashes |
| [ATTRIBUTION.md](ATTRIBUTION.md) | Dataset authors, licenses and modifications |
| [manifest.json](manifest.json) | Hashes of every file in this folder |

Publisher labels are deliberately visible, so this is a review aid, not a blind human test or a clean final evaluation. [Results](../../docs/RESULTS.md) own the interpretation; the [method](../../docs/METHOD.md) defines the comparison.
