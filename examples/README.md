# Public Evidence Snapshot

**Start with the [method and results page](index.html), then [listen to the recorded decisions](audio-comparison/index.html).** Everything here is a static site that any browser can open; the hosted copy is at https://faustinopalma.github.io/ModelMetis/.

| Evidence | Contents |
| --- | --- |
| [Simple-method comparison](audio-comparison/README.md) | 40 attributed ten-second excerpts, eight full-resolution DSP figures per excerpt, 48 recorded decisions with exact model inputs |
| [Simple-method summary](results/simple-method-summary.json) | Per-configuration counts, numerical controls, calibration, references, code binding and limits |
| [All simple-method attempts](results/simple-method-outcomes.json) | 68 recorded HTTP attempts, including four technical failures, with request/response hashes |
| [Other directions explored](archive/index.html) | Pruning review, crossed-study outcomes, family separation, diagram attribution and class-memory aggregates |
| [Manifest](manifest.json) | Hash of every published file |

Run `python -m scripts.check_examples` from the repository root to verify hashes, links, audio and the displayed decisions. For local browsing, serve this folder over HTTP so every browser plays the audio: `python -m http.server 8000 --bind 127.0.0.1 --directory examples`.

The recordings come from development work, and publisher labels are shown so every decision can be checked. [Results](../docs/RESULTS.md) own the interpretation; [publication policy](../docs/PUBLICATION.md) owns the release boundary.
