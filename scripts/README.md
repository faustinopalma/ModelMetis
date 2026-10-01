# Verify And Reproduce The Current DSP Evidence

**Opening or verifying the public evidence requires no cloud account or inference call.** Scientific recomputation and new paid inference are separate operations. The commands below run from the repository root; generated experiments always use a new output directory.

## Inspect The Committed Snapshot

Use the [hosted comparison](https://faustinopalma.github.io/ModelMetis/audio-comparison/) or the [local static-server quick start](../README.md#verify-without-cloud-access). Python 3.12 or later can verify the snapshot and staged publication boundaries using only the standard library:

```console
python -m scripts.check_examples
python -m scripts.check_publication
```

The first command checks committed evidence, hashes and links. The second checks the Git index, including credential patterns and restrictions on local artifacts. Neither accesses Azure or the source archives.

## Set Up Numerical Reproduction

Use an isolated Python environment with the project and DSP dependencies. The `dsp` extra declares bounded version families; the [Windows ARM64 snapshot](../ml/requirements-dsp-extensions-windows-arm64.txt) records the measured environment rather than a universal cross-platform lockfile.

```console
python -m venv .venv
```

Activate that environment using its platform's standard activation command, then:

```console
python -m pip install -e ".[dev,dsp]"
python -m pytest tests/test_dsp.py tests/test_dsp_extensions.py tests/test_dsp_similarity.py tests/test_audio_comparison.py -q
```

Two comparison-template tests execute JavaScript helpers and need Node.js on the path.

The shared console icon renderer is only needed for the older local workbench generators; the public publishers use the committed [icon markup](templates/icons.json). Some archival encoder campaigns require a separate x64 ML runtime; do not merge it into the application/DSP environment.

## Reproduce The Simple Method

The simple method's local evidence lives in `outputs/dsp-jin-v1`, `outputs/dsp-ottawa-v1`, `outputs/dsp-ottawa-v2` and `outputs/dsp-labeled-results-v1`, which a clone does not contain. With those folders and the source WAVs present, these commands make no model call and write only new directories:

| Operation | Command | Checks |
| --- | --- | --- |
| Recount all 68 attempts | `python -m scripts.evaluate_dsp_similarity report --output outputs/dsp-labeled-results-replay` | Rebuilds the aggregate and case audit; compare with `outputs/dsp-labeled-results-v1` |
| Regenerate the public simple-method snapshot | `python -m scripts.publish_simple_method --output outputs/public-simple-new` | Re-validates registrations, request/receipt/response hashes, decisions, contact-sheet figures and the documented counts |
| Regenerate the archived pruning snapshot | `python -m scripts.publish_evidence --output outputs/public-archive-new/archive/pruning-candidate --results` | Re-validates the pruning, family and attribution evidence |
| Reseal an assembled snapshot | `python -m scripts.publish_simple_method --seal examples` | Rewrites a manifest after deliberate replacement; reseal nested folders first |

The runner [evaluate_dsp_similarity.py](evaluate_dsp_similarity.py) registers datasets, builds rounds, submits requests and evaluates them; its `run` action is the only paid step. [Registered code](../registered/simple-method/README.md) preserves the exact runner and validator versions recorded by the experiments. The committed runner is the final version and can produce different request bytes. A new campaign therefore needs a new registration and output folder and cannot reuse consumed recordings as fresh evidence.

```console
python -m scripts.evaluate_dsp_similarity register --dataset jin --output outputs/dsp-jin-new
python -m scripts.evaluate_dsp_similarity new-round --output outputs/dsp-jin-new --round 01 --numerical-comparison
python -m scripts.evaluate_dsp_similarity run --output outputs/dsp-jin-new --round 01 --phase development --limit 8
```

`run` requires an authorized compatible model deployment, an Entra session and explicit approval; it incurs charges. Registration, round preparation and evaluation are local.

## Reproduce Archived Variants

| Operation | Command or owner | Additional input |
| --- | --- | --- |
| Recalculate family metrics | `python -m scripts.dsp_family_separation --output outputs/family-replay` | Frozen registered WAVs and extended-DSP evidence |
| Re-evaluate crossed pruning decisions | `python -m scripts.dsp_pruning_experiment evaluate --output outputs/dsp-pruning-cross-v1` | Immutable local requests, receipts, responses and sealed labels |
| Generate the essential pruning review | `python -m scripts.dsp_pruned_review --output outputs/audio-review-new` | Verified recorded pruning campaign and complete diagram/audio artifacts |
| Prepare an Ottawa class-memory pilot | `python -m scripts.dsp_memory_experiment prepare --output outputs/dsp-memory-new` | Audited complete Ottawa inventory; [protocol](../docs/DSP_MEMORY_PROTOCOL.md); no inference |
| Generate the next memory request | `python -m scripts.dsp_memory_experiment next --output outputs/dsp-memory-new --arm fixed` | Newly prepared registration; use `adaptive` for the other arm |
| Reconcile measured memory results | `python -m scripts.dsp_memory_inference evaluate --output outputs/dsp-memory-ottawa-v3` | Completed bound responses and both state journals; [results](../docs/DSP_MEMORY_RESULTS.md); no new inference |
| Prepare a new pruning campaign | [Pruning protocol](../docs/DSP_PRUNING_PROTOCOL.md) and `scripts.dsp_pruning_experiment prepare` | New registration and reviewed selection; preparation is local |

The class-memory runner `scripts.dsp_memory_inference run` and the pruning runner's `run` action submit paid requests. Their registrations bind the code that executed; edit them only under a new registration.

The complete private source folders are deliberately not in the clone. Obtain the versioned publisher data under their licenses and follow the study-specific import and registration contracts for scientific replay. The committed excerpts are an inspection subset, not every study's full sample set. Never present a replay of consumed data as a new clean evaluation.

## Keep Historical Work Separate

[Historical commands](../docs/LEGACY_COMMANDS.md) preserve earlier teacher, specialist, encoder, drone and DSP execution records. Some archived commands depend on unselected local assets or tools and are not the supported public quick start. [Experiment reports](../docs/EXPERIMENTS.md) own their outcomes. The current publication process follows [publication policy](../docs/PUBLICATION.md).
