# Public Evidence CI

[The Pages workflow](pages.yml) verifies the curated static snapshot and the indexed publication boundary using Python's standard library. Pull requests run validation; a successful `main` build publishes `examples/` to [GitHub Pages](https://faustinopalma.github.io/ModelMetis/) with short-lived workflow identity.

Application lifecycle tests, image builds, cloud deployment, training orchestration and promotion are planned as separate workflows, with acceptance criteria in the project validation and backlog documents.
