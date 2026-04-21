# Apps

This directory contains top-level runnable applications.

## Current Apps

- `web/` — primary React control surface

## Planned Apps

- `desktop/` — optional future top-level desktop shell entry
- `service/` — optional future top-level service wrapper if the Python core is extracted further

Rule:

- apps are runnable entrypoints
- shared logic should move into `packages/`
- apps must not deep-couple to each other

