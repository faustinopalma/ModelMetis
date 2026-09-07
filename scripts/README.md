# Automation

Directory reserved for reproducible scripts; it does not yet contain executable provisioning or application commands.

Automation to implement in order: toolchain and contract checks, local startup, deterministic fixture replay, teacher benchmarking, snapshot publication, ML job submission, cost reporting, and rollback testing. Deployment scripts will follow infrastructure approval.

Every command must report its duration, return a nonzero exit code on failure, verify that at least one item was processed when expected, and support repetition without duplicating effects. Use parameters and input files instead of credentials or complex payloads on the command line. Long operations have timeouts, budgets, and persistent state.
