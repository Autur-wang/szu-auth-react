# Repository Contract for Agents

This file summarizes the working contract for agents operating in this repository.

The canonical repository-level engineering policy is:

- `AI_NATIVE_HARNESS.md`

## Layering

- `apps/web/` is the frontend control plane
- `gym_bot/` is the automation and service core
- `gym_bot/app/` is the Electron shell
- `packages/` is the shared layer
- `docs/szu-booking/` is reference and prototype material only

Agents must preserve this layering.

## Source of Truth

- booking truth belongs to the Python core
- agent truth belongs to the Python core
- cookie truth belongs to the Python core
- frontend is a control surface, not the business source of truth
- Electron is a shell, not a second business UI

## Non-Trivial Feature Rule

A non-trivial feature is incomplete unless it includes:

1. a spec
2. a contract
3. a harness scenario
4. success-path verification
5. failure-path verification
6. meaningful logs or structured output

## Required Directories

Use and maintain:

- `apps/`
- `apps/web/`
- `packages/`
- `specs/`
- `harness/contracts/`
- `harness/scenarios/`
- `harness/fixtures/`
- `runtime/`

## Runtime Rule

Mutable runtime state must not spread through source directories.
Keep config, cookie cache, logs, replay artifacts, and state snapshots isolated in a runtime location.
