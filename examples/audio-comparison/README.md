# Simple Method Comparison

**[Open the comparison](index.html) to listen to each recording beside its references and inspect the recorded model decision.** It contains all 48 decisions of three configurations; select a collection to see each configuration with its own counts.

| Collection | Configuration | Decisions |
| --- | --- | --- |
| Jin: reports + distances | B, reports plus Welch spectral distances | 12 reserved right-microphone windows and 4 excluded-class tests |
| Ottawa: reports only | A, reports and instructions | 16 profile-2 development acquisitions |
| Jin: calibrated replay | C, calibrated distance rule, exploratory | The same 16 Jin inputs, decided after inspecting configuration B |

The input recording is on the left with its publisher class. A reference is on the right: Correct reference shows the publisher class, Model choice shows the class the model selected, and the arrows browse every reference. A reference marked withheld was left out of that request, so the expected answer is different. The note under each outcome gives the Welch distances supplied to the model, or for configuration A the recorded numerical control computed beside it.

The system analyzes each recording into eight figures and numerical measurements; the model studied the figures as resized contact-sheet cells together with the measurements. The page shows those figures at full resolution and plays the original ten-second excerpts. Link to a single decision with `index.html#<case-id>`, for example `index.html#jin-distances-excluded-T04`.

| Folder or file | Contents |
| --- | --- |
| `inputs/` | Exact transmitted text and response schema; each image part is replaced by its contact-sheet hash and cell list |
| `responses/` | Exact parsed decisions and original request/response hashes |
| `media/` | Content-addressed original WAV excerpts and full-resolution DSP figures |
| [provenance.json](provenance.json) | Per-record collection, class, audio hash, rate, duration and figure hashes |
| [ATTRIBUTION.md](ATTRIBUTION.md) | Dataset authors, licenses and modifications |
| [manifest.json](manifest.json) | Hashes of every file in this folder |

Publisher labels are shown with every decision so it can be checked. [Results](../../docs/RESULTS.md) own the interpretation; the [method](../../docs/METHOD.md) defines the comparison.
