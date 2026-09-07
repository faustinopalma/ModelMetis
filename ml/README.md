# ML Lifecycle

Directory reserved for Azure ML components and pipelines. No models, datasets, or jobs have been created.

Component implementation order: manifest validation, split preparation, baseline training, candidate training, calibration, independent evaluation, bundle registration, and reporting. Notebooks are allowed for exploration but must not be the pipeline's only implementation.

Use established libraries: PyTorch/torchvision for transfer learning, scikit-learn for baselines and metrics, and MLflow for experiments. Pin versions and the container environment after verifying compatibility. Separate heavy dependencies from runtime dependencies.

Each run records code, dependencies, seed, dataset and hashes, parameters, resources, duration, and estimated cost. Reproducibility does not mean bit-for-bit identity across different GPUs and platforms: define tolerances and checks. Preparation, calibration, and serving must use the same versioned preprocessing.

Training does not publish a candidate as champion. It produces artifacts and reports; promotion follows the [protocol](../docs/VALIDAZIONE.md) and requires separate approval.
