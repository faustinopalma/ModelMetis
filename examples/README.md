# Public Evidence Snapshot

**Start with the [method and results page](index.html), then [listen to the recorded decisions](audio-comparison/index.html).** Everything here is static: no backend, package installation, model call or credential is needed. The hosted copy is at https://faustinopalma.github.io/ModelMetis/.

| Evidence | Contents |
| --- | --- |
| [Simple-method comparison](audio-comparison/README.md) | 40 attributed ten-second excerpts, eight full-resolution DSP figures per excerpt, 48 recorded decisions with exact model inputs |
| [Simple-method summary](results/simple-method-summary.json) | Per-configuration counts, numerical controls, calibration, references, code binding and limits |
| [All simple-method attempts](results/simple-method-outcomes.json) | 68 recorded HTTP attempts, including four technical failures, with request/response hashes |
| [Archived variants](archive/index.html) | Pruning candidate review, crossed-study outcomes, family separation, diagram attribution and class-memory aggregates |
| [Manifest](manifest.json) | Hash of every published file |

Run `python -m scripts.check_examples` from the repository root to verify hashes, links, audio and the displayed decisions. For local browsing, serve this folder over HTTP: `python -m http.server 8000 --bind 127.0.0.1 --directory examples`. Some integrated browsers block WAV playback from `file://` pages.

These recordings were used during development and labels are visible. They support inspection of recorded evidence, not blind human testing or clean final evaluation. [Results](../docs/RESULTS.md) own the interpretation; [publication policy](../docs/PUBLICATION.md) owns the release boundary.
