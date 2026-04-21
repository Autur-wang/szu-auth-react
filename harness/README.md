# Harness Directory

This directory exists to make critical system behavior reproducible, inspectable, and safe to validate.

The harness layer is mandatory for this repository.

## Subdirectories

- `contracts/` for interface definitions
- `scenarios/` for replayable workflow cases
- `fixtures/` for deterministic test artifacts

## Goals

- make critical flows testable without production side effects
- make system behavior easy to understand for both humans and AI agents
- reduce debugging by replacing guesswork with replayable scenarios

