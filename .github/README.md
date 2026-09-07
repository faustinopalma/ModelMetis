# Planned CI/CD

No workflows are active. Add pipelines when real code and verification commands exist; avoid green pipelines that test nothing.

- Pull requests: contract validation, lint, typecheck, and fast tests; image builds and scans when available; no access to real data or secrets from untrusted contributions.
- Main: reproducible builds and image publication by digest; dev deployment only with an approved destination and budget.
- Training: explicit or coordinator-controlled execution, with a snapshot, budget, and maximum job count; no GPU training on every commit.
- Model release: offline reports, shadow evaluation, and canary rollout with gates independent of the code release.
- Production: protected environment, approval, least-privilege OIDC identity, and verified rollback.

The first implemented pipeline must actually run the tests from MM-004 and MM-005. Training permissions do not authorize model promotion.
