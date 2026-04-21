# Execution Checklist for Agents

Use this checklist before and during substantial work.

## Before Implementing

1. Identify the affected layer:
   - frontend
   - service core
   - Electron shell
   - specs/harness
2. Check whether a spec already exists.
3. Check whether a contract already exists.
4. Check whether a harness scenario already exists.
5. Check which source-of-truth document applies.

## Implementation Order

Preferred order for meaningful work:

1. update or create spec
2. update or create contract
3. update or create harness scenario
4. implement feature
5. verify logs and failure behavior
6. update docs

## Frontend Checklist

- no hidden business rules in React components
- API contracts are explicit
- UI exposes task and system state
- fake/demo behavior is clearly marked

## Python Checklist

- core logic stays reusable
- side effects stay behind clear boundaries
- task results are structured where possible
- code is harnessable without UI

## Electron Checklist

- Electron stays a shell
- no duplicate business UI
- desktop-only capability stays in IPC

## Completion Gate

Do not consider work complete if only the happy path works.

