# Harness Scenario Template

Use this template for replayable or testable workflow scenarios.

## 1. Scenario Name

- Name:
- Layer:
- Related feature:

## 2. Intent

What workflow is this scenario validating?

## 3. Preconditions

- config state
- runtime state
- fixture requirements
- dependency assumptions

## 4. Inputs

- direct inputs
- mocked inputs
- user actions if applicable

## 5. Execution Mode

- live
- mock
- dry-run
- replay

## 6. Expected State Transitions

- starting state
- intermediate phases
- terminal state

## 7. Expected Outputs

- result payload
- UI state if applicable
- logs
- error surface if applicable

## 8. Failure Branches

- what should happen if a dependency fails?
- what should happen if validation fails?

## 9. Artifacts

- fixtures used
- snapshots produced
- logs captured

## 10. Pass Criteria

- exact conditions required for this scenario to pass
