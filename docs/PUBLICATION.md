# Publish Curated Evidence Without Exposing Operational State

**The release under `examples/` is an explicit selection, not permission to publish all local data.** It includes the current review and evidence needed to inspect its conclusions. New experiments are not automatically published.

| Included | Purpose |
| --- | --- |
| Sixteen ten-second audio derivatives and four plots per recording | Query/reference listening and visual comparison |
| Eight primary candidate decisions and two repeats | Preserve success, rejection and the unsafe disagreement |
| Exact selected input text and response schema, with contact-sheet hashes | Inspect instructions and numerical evidence without repeated image payloads |
| Parsed model decisions and original request/response hashes | Preserve substantive output without service/resource metadata |
| Forty-six crossed-study outcomes and family-separation summaries | Verify comparisons and denominators |
| Content-addressed media, attribution and manifests | Deduplicate and check integrity |

Credentials, CLI caches, complete source archives, model checkpoints, runtime caches, unselected raw HTTP envelopes and intermediate runs remain excluded. Candidate final-evaluation acquisitions are not part of this development snapshot.

[Audio attribution](../examples/audio-comparison/ATTRIBUTION.md) identifies the CC BY 4.0 authors, versions and modifications. [Provenance](../examples/audio-comparison/provenance.json) binds individual derivatives. Dataset licenses do not assign a blanket license to the repository's original code; no software license has been selected implicitly.

## Validate Before Deploying

`python -m scripts.check_examples` verifies the complete snapshot manifest, media hashes, nonempty mono audio, relative links, displayed decisions, outcome coverage and common credential/local-path patterns. `python -m scripts.check_publication` scans the Git index, not only the working directory. Audio is allowed only in the content-addressed curated media directory. These prevent accidental disclosure; they are not exhaustive secret detection.

GitHub Pages deploys only `examples/` after validation. It exposes no backend, model endpoint, authentication token or upload capability. Pull requests can validate but cannot deploy. The site is a research demonstration, not a diagnostic service.

The snapshot's Git attributes disable automatic line-ending conversion so checked-out bytes match the published hashes on Windows and Linux. Intentional updates must regenerate the snapshot manifest; do not edit a hashed file without resealing and verifying the release.

## Regenerate Deliberately

The [publication adapter](../scripts/publish_evidence.py) reads verified local study artifacts, externalizes unchanged media and exports selected evidence. Generate into a new temporary directory, review provenance, then deliberately replace the public snapshot. Never rewrite frozen experiment inputs or receipts to improve an example.

Full source material remains under ignored `data/`, `artifacts/` and `outputs/`. Its absence does not prevent opening or validating the committed examples. Scientific replay needs the sources, DSP dependencies and, only for new inference, explicit model access and a separate registration.
