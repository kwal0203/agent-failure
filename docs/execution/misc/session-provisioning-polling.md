# Session provisioning status is polling-based (future shift to event-driven)

## Summary
The frontend currently determines provisioning progress by polling session metadata (`GET /api/v1/sessions/{session_id}`) while state is `PROVISIONING`.

This works, but it is not ideal for responsiveness, efficiency, or reconnect behavior. We should shift provisioning status updates to an event-driven model over the session websocket.

## Current behavior
- Frontend performs an initial metadata fetch on page load.
- While metadata state is `PROVISIONING`, frontend polls every 2 seconds.
- Frontend websocket receives one initial `SESSION_STATUS` message on connect, but there is no confirmed ongoing push of status transitions for provisioning lifecycle changes.

## Why this is an issue
- Extra load from periodic polling across active learners.
- Slower UX updates (bounded by polling interval).
- Potential inconsistency between stream events and polled metadata during network jitter/reconnect windows.
- More client complexity than a stream-first status model.

## Desired future state
- `SESSION_STATUS` becomes stream-first source of truth for provisioning/active/failed transitions.
- Backend emits status updates whenever session lifecycle state or runtime substate changes.
- Frontend uses polling only as fallback when stream is disconnected or stale.

## Proposed implementation direction
1. Backend:
- Emit `SESSION_STATUS` on meaningful state transitions (not only initial websocket connect).
- Include `state`, `runtime_substate`, `interactive`, and timestamp in each message.

2. Frontend:
- Drive session status chip and provisioning completion directly from stream `SESSION_STATUS` events.
- Keep metadata polling as fallback only when stream is unavailable/stale.
- Add stale-status threshold (example: if no status update for N seconds while provisioning, trigger fallback poll).

3. Reliability:
- On websocket reconnect, send current `SESSION_STATUS` immediately (already done) and continue transition pushes.
- Add tests for transition ordering and reconnect behavior.

## Acceptance criteria
- Provisioning -> Active/Failed transitions appear in UI without relying on fixed-interval polling.
- Polling does not run during healthy connected streaming, except fallback path.
- Reconnect recovers correct current status and continues receiving updates.
- Integration test coverage exists for status transitions over websocket.

## Notes
This is intentionally logged as a future improvement item and not required for current lab UI correctness.
