# AI-Native and Harness Engineering Contract

This repository must be a working example of both:

- AI-native product engineering
- harness-first systems engineering

This file is the repository-level engineering contract.
It is not optional guidance.

If a future implementation conflicts with this file, this file wins.

## 1. Repository Intent

This repository is not just a frontend demo and not just a booking bot.
It must evolve into a product-grade system with:

- a React control surface
- a Python automation core
- an Electron desktop shell
- deterministic harnesses for validation
- LLM-readable contracts for every important workflow

The target standard is:

- easy for humans to operate
- easy for AI agents to understand
- easy to test without production side effects
- easy to replay, inspect, and debug

## 2. What "AI-Native" Means Here

In this repository, AI-native means:

- core workflows are explicit, not hidden in UI-only behavior
- system state is inspectable and serializable
- modules expose stable contracts
- logs and errors are meaningful and machine-readable
- important decisions live in repository documents, not only in chat history
- each feature can be understood and operated by an agent without reverse-engineering the whole codebase

AI-native code in this repo must be:

- small enough to reason about
- named clearly
- contract-first
- deterministic where possible
- documented at boundaries

## 3. What "Harness Engineering" Means Here

In this repository, harness engineering means:

- every critical workflow must be runnable in a controlled test harness
- all dangerous or irreversible actions must have dry-run or simulated paths
- important scenarios must be replayable
- external dependencies must have mockable seams
- success and failure must be observable through structured outputs

No critical flow should require "just click around manually and hope."

## 4. Mandatory Architectural Rules

### 4.1 Layering

The repository must preserve this layering:

1. `apps/web/` is the frontend control plane
2. `gym_bot/` is the automation and service core
3. `gym_bot/app/` is the desktop shell only
4. `packages/` is the shared layer for contracts, config, and UI reuse
5. `docs/szu-booking/` is reference material and product prototype only

The UI must not directly implement booking logic.
The automation core must not rely on frontend state.
The Electron layer must not become a second business UI.

### 4.2 Single Source of Truth

- Booking state belongs to the Python core.
- Agent state belongs to the Python core.
- Cookie validity belongs to the Python core.
- Frontend config is an editor and viewer, not the source of truth.
- Electron is a launcher and capability bridge, not the source of truth.

### 4.3 Runtime Isolation

Generated runtime state must not leak into source directories.

All mutable runtime data must converge into a dedicated runtime location, for example:

- config
- cookie cache
- agent state
- transient logs
- replay artifacts
- fixture snapshots generated during harness runs

## 5. Mandatory Deliverables for Every Non-Trivial Feature

Every non-trivial feature must add all of the following:

1. a spec entry
2. a contract entry
3. at least one harness scenario
4. at least one success-path verification
5. at least one failure-path verification
6. observable logs or structured result output

If a feature cannot be verified without production access, it must still provide:

- a dry-run mode
- a stubbed mode
- or a replay mode

## 6. Repository-Level Constraints

### 6.1 Frontend Constraints

Frontend code under `apps/web/src/` must:

- consume backend contracts instead of embedding hidden business rules
- display explicit task and system state
- surface errors with actionability
- separate layout, API access, state, and presentational components
- avoid fake data in production paths unless clearly marked as mock/demo

Frontend code must not:

- become the source of booking truth
- persist authoritative business state in arbitrary browser storage
- silently invent backend assumptions

### 6.2 Python Core Constraints

Python code under `gym_bot/` must:

- expose reusable service-layer functions
- keep side effects behind clear boundaries
- return structured results wherever practical
- preserve deterministic seams for mocking
- support harness invocation without UI

Python code must not:

- bury critical logic only inside one-off CLI flow
- mix runtime file paths everywhere without central control
- rely on hidden globals for important state transitions

### 6.3 Electron Constraints

Electron code under `gym_bot/app/` must:

- remain a shell and local capability layer
- open login windows
- bridge desktop-only APIs
- load the main React interface

Electron code must not:

- become a second primary UI implementation
- duplicate full business workflows already present in React
- own business state that should belong to the backend core

## 7. Required Repository Structure

The following directories are now part of the intended engineering model:

- `apps/`
- `apps/web/`
- `packages/`
- `specs/`
- `harness/`
- `harness/contracts/`
- `harness/scenarios/`
- `harness/fixtures/`
- `runtime/`

These directories define how features are specified, constrained, and verified.

## 8. Specs Rules

All meaningful features should be represented in `specs/`.

A feature spec should include:

- feature name
- owner area
- problem statement
- user-visible behavior
- backend behavior
- failure modes
- observability requirements
- harness coverage requirement
- definition of done

Specs should be concise, operational, and easy for an AI agent to parse.

## 9. Contract Rules

Contracts live under `harness/contracts/`.

Contracts should exist for:

- HTTP endpoints
- Electron IPC interfaces
- internal service boundaries where state transitions matter
- structured task results

A contract should define:

- input shape
- output shape
- error shape
- side effects
- idempotency expectations
- timeout behavior if relevant

If an interface exists without a contract, it is incomplete.

## 10. Harness Scenario Rules

Scenarios live under `harness/scenarios/`.

Each critical workflow must have named scenarios, for example:

- `auth.cookie_valid`
- `auth.manual_login_required`
- `booking.query_success`
- `booking.immediate_success`
- `booking.no_venue_available`
- `agent.daily_cycle_success`
- `agent.cookie_refresh_fail`
- `post_booking.payment_fail`

Every scenario should specify:

- preconditions
- inputs
- mocks or live dependencies
- expected outputs
- expected state transitions
- expected logs

## 11. Fixture Rules

Fixtures live under `harness/fixtures/`.

Fixtures should be used for:

- API payload snapshots
- mocked booking responses
- mocked auth redirects
- agent state snapshots
- log examples

Fixtures must be:

- deterministic
- minimal
- sanitized
- easy to diff

Never store real secrets in fixtures.

## 12. Observability Rules

Every critical workflow must produce inspectable output.

At minimum, each important path should expose:

- current phase
- last transition time
- success or failure result
- structured error code
- human-readable message

Logs must help both:

- a human operator
- an AI agent trying to diagnose the system

Bad logs:

- vague
- chatty but useless
- missing identifiers
- missing failure reason

Good logs:

- phase-aware
- action-aware
- concise
- structured when possible

## 13. Dry-Run and Safety Rules

Any dangerous or state-changing workflow should support one of:

- `dry-run`
- `mock`
- `replay`

This is especially important for:

- booking submission
- payment
- agent automation
- cookie mutation

No major workflow should be validated only by hitting live systems first.

## 14. Testing Standard

Unit tests are necessary but not sufficient.

Each important workflow should have:

- unit coverage for core logic
- service-level verification
- harness scenario coverage
- at least one regression artifact or replay path

The expected testing pyramid for this repo is:

1. pure logic tests
2. service and contract tests
3. harness scenario tests
4. limited live smoke tests

## 15. Definition of Done

A feature is not done unless:

- implementation exists
- spec exists
- contract exists
- harness scenario exists
- logs are meaningful
- failure paths are handled
- docs are updated

If only the UI works, it is not done.
If only the script works, it is not done.
If only the happy path works, it is not done.

## 16. Anti-Patterns Forbidden in This Repository

The following are explicitly forbidden:

- hidden business rules only inside React components
- unstructured cross-layer coupling
- second business UI inside Electron
- critical behavior without harness coverage
- runtime secrets committed into source control
- flows that only work by manual operator intuition
- giant undocumented modules with mixed responsibilities
- “just run it live and see what happens” as the primary validation method

## 17. Immediate Next-Step Standard

All future implementation work should align with this order:

1. write or update spec
2. define or update contract
3. add or update harness scenario
4. implement feature
5. verify logs and failure paths
6. update documentation

This order is mandatory for major work.
