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

Use an isolated Python environment with the project and DSP dependencies. The following bounded version families support the source implementation; the [Windows ARM64 snapshot](../ml/requirements-dsp-extensions-windows-arm64.txt) records the measured environment rather than a universal cross-platform lockfile.

```console
python -m venv .venv
```

Activate that environment using its platform's standard activation command, then:

```console
python -m pip install -e ".[dev,audit,ml]"
python -m pip install "matplotlib>=3.10,<4" "pillow>=12,<13" "PyWavelets>=1.8,<2" "jsonschema>=4.25,<5"
python -m pytest tests/test_dsp.py tests/test_dsp_extensions.py tests/test_audio_comparison.py -q
```

The shared console icon renderer is only needed when regenerating the original self-contained review, not for opening the committed demo. Some archival encoder campaigns require a separate x64 ML runtime; do not merge it into the application/DSP environment.

## Choose The Reproduction Level

| Operation | Command or owner | Additional input |
| --- | --- | --- |
| Verify public release | `python -m scripts.check_examples` | Committed `examples/` only |
| Recalculate family metrics | `python -m scripts.dsp_family_separation --output outputs/family-replay` | Frozen registered WAVs and extended-DSP evidence |
| Re-evaluate crossed decisions | `python -m scripts.dsp_pruning_experiment evaluate --output outputs/dsp-pruning-cross-v1` | Immutable local requests, receipts, responses and sealed labels |
| Generate essential local review | `python -m scripts.dsp_pruned_review --output outputs/audio-review-new` | Verified recorded pruning campaign and complete diagram/audio artifacts |
| Export a new public candidate snapshot | `python -m scripts.publish_evidence --output outputs/public-candidate/audio-comparison --results` | Verified local v15 and completed study artifacts; inspect before publishing |
| Prepare a new pruning campaign | [Pruning protocol](../docs/DSP_PRUNING_PROTOCOL.md) and `scripts.dsp_pruning_experiment prepare` | New registration and reviewed selection; preparation is local |
| Submit model requests | Registered runner's `run` action | Explicit authorization, own compatible model resource and identity; incurs charges |

The complete private source folders are deliberately not in the clone. Obtain the versioned publisher data under their licenses and follow the study-specific import/registration contracts for scientific replay. The committed sixteen clips are an inspection subset, not enough to reproduce every study's full sample set. Never present a replay of consumed data as a new clean evaluation.

## Keep Historical Work Separate

[Historical commands](../docs/LEGACY_COMMANDS.md) preserve earlier teacher, specialist, encoder, drone and DSP execution records. Some archived commands depend on unselected local assets or tools and are not the supported public quick start. [Experiment reports](../docs/EXPERIMENTS.md) own their outcomes. The current publication process follows [publication policy](../docs/PUBLICATION.md).
