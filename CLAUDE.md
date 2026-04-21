# Repository Claude Entry

This is the root Claude entry file for the repository.

The canonical repository rules do not live here.
They live in `.agent/`.

## Required Read Order

Before making substantial changes, read:

1. `.agent/README.md`
2. `.agent/repo-contract.md`
3. `.agent/ui-contract.md`
4. `.agent/execution-checklist.md`

Then consult:

- `AI_NATIVE_HARNESS.md`
- `DESIGN.md`
- `风格.md`
- `TODO.md`
- `specs/`
- `harness/`

## Important Rule

Do not treat local implementation quirks as repository policy when an explicit contract file already exists.

The repository must be operated as:

- AI-native
- harness-first
- contract-driven
- layered across frontend, service core, and Electron shell

## Artifact Creation Rule

For meaningful new work, create or update:

1. a spec
2. a contract
3. a harness scenario

Use the templates in `.agent/`:

- `.agent/spec-template.md`
- `.agent/contract-template.md`
- `.agent/scenario-template.md`

