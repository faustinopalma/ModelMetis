# Public Evidence CI

[The Pages workflow](workflows/pages.yml) verifies the curated static snapshot and the indexed publication boundary using Python's standard library. Pull requests run validation only. A successful `main` build publishes only `examples/` to GitHub Pages, using short-lived workflow identity; it does not run model inference, training, Azure deployment or the application backend.

Application lifecycle tests, image builds, private-cloud deployment, training orchestration and operational promotion are separate planned workflows. Their acceptance criteria remain in the project validation and backlog documents. Publishing research evidence does not authorize or promote a diagnostic model.
