# Local Data and Artifacts

Do not add production images, operational labels, gold datasets, weights, dumps, or sensitive exports to the repository. The original project sources remain in the root; this directory covers data from future executions.

Real data resides in authorized storage and is referenced through versioned manifests with hashes and lineage. Local working artifacts are ignored by Git. Small synthetic or redistributable fixtures may be added under tests with their license and provenance, after review.

Before ingestion, define retention, permissions, and permitted training use. A public dataset is not automatically suitable for the task or unrestricted in use. Do not use an anomaly-detection collection as evidence for multiclass classification without verifying its taxonomy and annotations.

See the [public audio dataset assessment](../docs/AUDIO_DATASETS.md) for motor-fault sources, access and licensing constraints, and a recommended starting dataset. No dataset has been downloaded or approved for training yet.
