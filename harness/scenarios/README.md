# Scenarios

Scenarios define replayable workflow cases.

Initial scenario set for this repository should include:

- `auth.cookie_valid`
- `auth.manual_login_required`
- `booking.query_success`
- `booking.immediate_success`
- `booking.no_venue_available`
- `agent.daily_cycle_success`
- `agent.cookie_refresh_fail`
- `post_booking.payment_fail`

Each scenario should define:

- setup
- inputs
- mocks or live dependency expectations
- expected outputs
- expected state transitions
- expected logs

