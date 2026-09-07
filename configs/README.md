# Configuration

Directory reserved for tasks, prompts, routing policies, gates, and non-sensitive settings. It does not yet contain operational configurations: thresholds and the teacher model must be selected after F0 and benchmarking.

Planned subdivisions: `tasks` for taxonomies and critical classes, `prompts` for instructions and few-shot references, `policies` for eligibility and fallback, `evaluation` for gates, and `environments` for non-secret references. Create these subdivisions when the first real file exists, without duplicating empty configurations.

Each execution records the ID, version, and hash of the resolved configuration. No gold test references in prompts. No tokens, passwords, or connection strings; endpoints and deployment names come from environment configuration. A missing threshold must block activation of the hybrid policy.
