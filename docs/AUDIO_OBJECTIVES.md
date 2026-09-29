# Audio Objectives By Ambition

Four candidate objectives reduce the supported machine domain first, then the diagnostic detail. None has established operational reliability in this project. Domain, error limits, useful coverage and human effort must be specified before another experiment.

| Level | Output | Required data | Verification |
| --- | --- | --- | --- |
| 1. Diagnosis across machine types | Known fault identity across different machines and operating conditions | Few confirmed fault references and independent machines/acquisitions | Per-fault error, coverage and review demand, including unsupported cases |
| 2. Diagnosis within one machine family | Known fault identity within a fixed family, operating envelope and recording protocol | Confirmed references, representative family recordings and speed/load context where available | Other units and later acquisitions under the defined protocol |
| 3. Anomaly detection within that scope | Departure from verified normal behavior; cause unknown | Normal recordings of the monitored machine covering legitimate variability | Missed anomalies, false alerts/hour, detection delay and inspection effort |
| 4. Change monitoring within that scope | Persistent acoustic change relative to the same machine's history | Comparable historical recordings; the previous state need not be certified normal | Documented changes, nuisance-alert frequency and maintenance usefulness |

The scale reduces the application claim, not necessarily algorithmic difficulty. Levels 2-4 retain the same controlled machine family and acquisition protocol. An acoustic anomaly does not prove mechanical failure; normal-sounding operation does not certify health. A change after repair may be real without being abnormal.

EXP-009 failed cross-drone transfer with zero geometric-policy coverage. EXP-010 found limited condition-associated similarity and impure clusters. Jin results concern four previously examined query recordings with acquisition confounds. These experiments do not validate heavy-vehicle diagnosis or any lower level in the table.

## Separate Choices

- Grouping by condition requires independent evidence that members share a condition. One reviewed representative cannot verify a cluster.
- Retrieval for a technician requires useful rankings and measured search-effort reduction. Diagnosis remains human, changing the occasional-intervention workload.
- Teacher-to-specialist learning requires a competent teacher first, then independent evidence that silver-trained specialists preserve quality at lower total cost.

## Shared Constraints

Keep initial annotation sparse and count reference collection, calibration, corrections and audits. Normal recordings and operational context are acquisition prerequisites. Independent evaluation needs separately accounted truth. Preserve physical-unit/acquisition splits, masking and gold/silver provenance. Windows from one recording are not independent machines.

The [video study](BACKLOG.md#deferred-video-task) remains deferred. See [experiments](EXPERIMENTS.md), [current state](CONTEXT.md) and the [sparse-annotation contract](ADAPTIVE_MODELS.md#sparse-human-annotation-contract).
