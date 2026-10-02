# Local Data and Artifacts

Local source archives, sanitized audio, sealed references, model caches and ML runtimes live here and are ignored by Git. Raw recordings, sample-level labels, weights, credentials and sensitive exports must remain unpublished.

Preserve versioned manifests, hashes and acquisition lineage. Small synthetic or redistributable test fixtures require explicit license/provenance. Cloud storage remains subject to private-access requirements.

Before ingestion, define retention, permissions, and permitted training use. A public dataset is not automatically suitable for the task or unrestricted in use. Do not use an anomaly-detection collection as evidence for multiclass classification without verifying its taxonomy and annotations.

Ottawa, AI Mechanic, Jin and drone sources have been downloaded and audited. See [dataset evidence](../docs/AUDIO_DATASETS.md) for rights and limitations. Existing splits and artifacts are immutable; consumed evaluation data is not fresh confirmation data.

## Fetch Sources From Their Publishers

Raw source files stay out of the repository. Download them from the original publisher with the provided scripts, which place them under `data/raw/`.

| Source | Attribution | Fetch and audit |
| --- | --- | --- |
| [MAFAULDA](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html) | The data used in this analysis is the MAFAULDA (Machinery Fault Database) provided by the Signals, Multimedia, and Telecommunications Laboratory at UFRJ. | `python -m scripts.audit_mafaulda --download --output outputs/mafaulda-audit-new` |
| [UORED-VAFCLS v5](https://data.mendeley.com/datasets/y2px5tg92h/5) | Sehri, M. and Dumond, P. (2023), University of Ottawa Rolling-element Dataset, Mendeley Data V5, doi:10.17632/y2px5tg92h.5, CC BY 4.0. | `python -m scripts.fetch_mendeley --dataset y2px5tg92h --version 5 --prefix 3_MatLab --output data/raw/uored-v5`, then `python -m scripts.audit_bearing_sources uored --root data/raw/uored-v5 --output outputs/uored-audit-new/summary.json` |
| [FSTF bearing sound v1](https://data.mendeley.com/datasets/n9y9c7xrz3/1) | Ait Ben Ahmed, A. (2023), Sound Datasets of a Rolling Element Bearing under Various Operating Conditions, Mendeley Data V1, doi:10.17632/n9y9c7xrz3.1, CC BY 4.0. | `python -m scripts.fetch_mendeley --dataset n9y9c7xrz3 --version 1 --output data/raw/fstf-v1`, then `python -m scripts.audit_bearing_sources fstf --root data/raw/fstf-v1 --output outputs/fstf-audit-new/summary.json` |
