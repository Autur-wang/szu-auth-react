# Agent Entry Point

This directory is the canonical agent-facing entry point for this repository.

Use this directory as the first stop before making meaningful changes.

## Read Order

1. `.agent/repo-contract.md`
2. `.agent/ui-contract.md`
3. `.agent/execution-checklist.md`
4. use templates in `.agent/` when creating new feature artifacts

Then consult the source documents those files point to:

- `AI_NATIVE_HARNESS.md`
- `DESIGN.md`
- `风格.md`
- `TODO.md`
- `specs/`
- `harness/`

## Templates

Use these templates when starting new work:

- `.agent/spec-template.md`
- `.agent/contract-template.md`
- `.agent/scenario-template.md`

## Purpose

This repository is expected to be:

- AI-native
- harness-first
- contract-driven
- layered across frontend, service core, and desktop shell

This directory exists so an agent does not need to infer repository standards from scattered files.
