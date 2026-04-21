# Web App

This is the primary frontend control plane for the repository.

## Responsibilities

- render the user-facing control surface
- display booking, auth, and agent state
- edit configuration through explicit backend contracts
- remain a consumer of backend truth, not the source of truth

## Rule

Do not place authoritative booking logic inside this app.

