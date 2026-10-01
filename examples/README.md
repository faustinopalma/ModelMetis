# Public Evidence Snapshot

Use the [hosted version](https://faustinopalma.github.io/ModelMetis/) or the repository's [local static-server quick start](../README.md#verify-without-cloud-access). [index.html](index.html) contains selected results and [audio-comparison/index.html](audio-comparison/index.html) contains the latest candidate review. No application backend, package installation or model credentials are required; HTTP also avoids integrated-browser restrictions on local WAV files.

| Evidence | Contents |
| --- | --- |
| [Audio comparison](audio-comparison/README.md) | Sixteen excerpts, paired plots, eight primary decisions and two repeats |
| [Crossed outcomes](results/pruning-decisions.json) | Forty-six outcomes with request/response hashes |
| [Crossed summary](results/pruning-summary.json) | Factorial, regression, targeted-removal and repeat comparisons |
| [Family separation](results/family-separation.json) | Within/between-family metrics and forced-label outcomes |
| [Diagram attribution](results/diagram-audit.json) | Reference-only surveys and the eight paired audited decisions |
| [Manifest](manifest.json) | Snapshot file hashes |

[Results](../docs/RESULTS.md) owns interpretation; [publication policy](../docs/PUBLICATION.md) owns release boundaries. This is consumed, truth-visible evidence, not an untouched evaluation set. Run `python -m scripts.check_examples` from the repository root to verify it.
