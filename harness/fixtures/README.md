# Fixtures

Fixtures are deterministic artifacts used by harness runs and tests.

Use fixtures for:

- mocked auth responses
- mocked booking payloads
- agent state snapshots
- result payload examples
- log examples

Rules:

- keep them minimal
- keep them sanitized
- keep them diff-friendly
- never store real secrets
