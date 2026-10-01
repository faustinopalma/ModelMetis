# Publish Curated Evidence Without Exposing Operational State

**The release under `examples/` is an explicit selection, not permission to publish all local data.** It contains the simple-method evidence needed to check its conclusions and the archived pruning review. New experiments are not automatically published.

| Included | Purpose |
| --- | --- |
| 40 ten-second audio derivatives with all eight model-facing figures each | Listening and visual comparison of every simple-method decision |
| 48 simple-method decisions in three separate collections | Successes, missed recognitions, correct and wrong rejections |
| Exact transmitted text and response schema, with contact-sheet hashes and cell lists | Inspect instructions, measurements and distances without repeated image payloads |
| Parsed model decisions and original request/response hashes | Preserve substantive output without service or resource metadata |
| All 68 simple-method attempt outcomes and a summary with controls and code binding | Verify denominators, technical failures and configuration boundaries |
| Archived pruning review, 46 crossed-study outcomes, family-separation and attribution summaries | Preserve later negative findings |
| Content-addressed media, attribution and manifests | Deduplicate and check integrity |

Credentials, CLI caches, account and subscription identifiers, complete source archives, model checkpoints, runtime caches, unselected raw HTTP envelopes, class-memory raw artifacts and intermediate runs remain excluded. Reserved final-evaluation acquisitions are not part of this development snapshot.

[Simple-method attribution](../examples/audio-comparison/ATTRIBUTION.md) and [archive attribution](../examples/archive/pruning-candidate/ATTRIBUTION.md) identify the CC BY 4.0 authors, versions and modifications; each folder's `provenance.json` binds individual derivatives. Dataset licenses do not assign a blanket license to the repository's original code; no software license has been selected implicitly.

## Validate Before Deploying

`python -m scripts.check_examples` verifies the complete snapshot manifest, media hashes, nonempty mono audio, relative links, displayed decisions, input/decision pairing, published counts and common credential/local-path patterns. `python -m scripts.check_publication` scans the Git index, not only the working directory. Audio is allowed only in the two content-addressed media directories. These prevent accidental disclosure; they are not exhaustive secret detection.

GitHub Pages deploys only `examples/` after validation. It exposes no backend, model endpoint, authentication token or upload capability. Pull requests can validate but cannot deploy. The site is a research demonstration, not a diagnostic service.

The snapshot's Git attributes disable automatic line-ending conversion so checked-out bytes match the published hashes on Windows and Linux. Intentional updates must regenerate the snapshot manifest; do not edit a hashed file without resealing and verifying the release.

## Regenerate Deliberately

The [simple-method publisher](../scripts/publish_simple_method.py) and the [archive publisher](../scripts/publish_evidence.py) read verified local study artifacts, re-validate every recorded decision, externalize unchanged media and export selected evidence. Generate into new directories, review them, copy them into `examples/`, add the hand-maintained `README.md` and `ATTRIBUTION.md` files, then reseal. The [reproduction guide](../scripts/README.md) lists the commands. Never rewrite frozen experiment inputs or receipts to improve an example.

Full source material remains under ignored `data/`, `artifacts/` and `outputs/`. Its absence does not prevent opening or validating the committed examples. Scientific replay needs the sources, DSP dependencies and, only for new inference, explicit model access and a separate registration.
