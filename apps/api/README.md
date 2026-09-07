# API

Directory reserved for the FastAPI application; code is not implemented yet. It exposes inference, feedback, request lookup, and authorized administrative operations. It reuses the [core](../../src/modelmetis/README.md) and [contracts](../../contracts/README.md), without containing training logic or hardcoded routing thresholds.

First increment: health/readiness checks, a testable authentication abstraction, image acquisition, `teacher_only` inference with a simulated provider, an idempotent ledger, and append-only feedback. Separate application status from the label: abstention is not a successful classification.

HTTP endpoints and the choice between an immediate response and an asynchronous request will be defined in the v1 contract based on the SLO. Limit uploads and use references to authorized assets; no arbitrary URL downloads or secrets in the browser.
