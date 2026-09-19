# Application Core

The Python `src` package implements the local audio-review API and separate experiment workers. [audio.py](audio.py) validates bounded integer PCM WAV; [repository.py](repository.py) owns the SQLite schema, persistent audio, and atomic review/history revisions; [api.py](api.py) exposes the FastAPI routes; [settings.py](settings.py) and [server.py](server.py) restrict operation to local development. [learning.py](learning.py) enforces silver-label contracts; [simulation.py](simulation.py), [audio_models.py](audio_models.py) and [audio_teacher.py](audio_teacher.py) implement the command-line experiments. Packaging is defined in [pyproject.toml](../../pyproject.toml); Azure inference and ML dependencies are optional extras, separate from the review API. No agent framework dependency is included.

The repository is a small concrete storage boundary called by the API. A future private blob/conditional-revision adapter must preserve the same revision-conflict semantics. It is not implemented or claimed to be cloud-compatible at the storage level. There is no reviewer authentication or actor attribution yet. See the [API README](../../apps/api/README.md) for format restrictions, persistence tradeoffs, and the production guard.

The [working context](../../docs/CONTEXT.md) controls the data and learning requirements. New uploads receive opaque names and are reconstructed without ancillary WAV metadata. `RecordingRepository.model_input` returns only a random sample ID and canonical audio; the review API uses explicit fields and excludes publisher reference labels, including legacy columns. These local controls do not replace the separate source/evaluation store, grouped partitions, or process permissions required before real teacher collection and student training.

Modules to introduce when required by the backlog:

| Module | Responsibility |
| --- | --- |
| `domain` | Tasks, predictions, revisions, snapshots, and releases |
| `routing` | Eligibility, abstention, fallback, and reasons |
| `teachers` | Provider interface and Foundry adapter |
| `students` | Specialist bundle invocation and validation |
| `data_engine` | Provenance, selection, deduplication, and snapshots |
| `review` | Assignment, concurrent revisions, and adjudication |
| `lifecycle` | States, budgets, training requests, and approvals |
| `adapters` | Blob, PostgreSQL, Service Bus, and Azure ML |
| `telemetry` | Correlation, metrics, and sensitive-data redaction |

The API and worker call the same application services. Transitions are persistent and deterministic. A future agent may use restricted tools to read reports and propose actions; it cannot independently change gates, privileges, or budgets.
