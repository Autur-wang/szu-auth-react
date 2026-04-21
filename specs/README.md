# Specs Directory

This directory is the human-readable and AI-readable source of truth for feature intent.

Every meaningful feature in this repository should eventually have a spec file here.

## What belongs here

- booking workflow specs
- authentication flow specs
- agent lifecycle specs
- frontend control-plane specs
- Electron shell responsibility specs

## Minimum spec format

Each spec should include:

1. feature name
2. problem statement
3. user-visible behavior
4. system behavior
5. failure modes
6. observability requirements
7. harness scenarios required
8. definition of done

## Rule

If a feature changes behavior but no spec changes, that change is incomplete.

