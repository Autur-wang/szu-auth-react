# Contract Template

Use this template for API, IPC, or important internal service boundaries.

## 1. Contract Name

- Name:
- Layer: HTTP / IPC / internal service
- Owner:

## 2. Purpose

What stable boundary does this contract define?

## 3. Input Shape

- fields
- types
- required vs optional
- validation rules

## 4. Output Shape

- success payload
- important state fields
- identifiers returned

## 5. Error Shape

- error code
- error message
- retryable or not

## 6. Side Effects

- files changed
- runtime state changed
- network actions
- notifications triggered

## 7. Idempotency Rules

- is repeated invocation safe?
- what happens on duplicate calls?

## 8. Timeout / Cancellation Rules

- expected timeout
- cancellation behavior
- cleanup behavior

## 9. Observability

- expected logs
- expected state transitions
- metrics or counters if applicable

## 10. Harness Coverage

Which harness scenarios verify this contract?

