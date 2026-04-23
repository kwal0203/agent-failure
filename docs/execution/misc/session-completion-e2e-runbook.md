# Session Completion E2E Runbook

This runbook validates end-to-end completion behavior for the control-plane path:

- objective completion projection
- completion event emission (`session.completed.v1`)
- completion projection worker
- metadata API readback
- frontend completion indicator behavior (metadata-driven)

## Preconditions

- Control-plane API is running and reachable.
- Objective worker is running or can be executed once.
- Completion worker is running or can be executed once.
- Frontend is running (optional UI check).
- A valid auth token is available for API calls.

## Automated Targeted Checks

Run targeted tests that cover deterministic completion + replay:

```bash
uv run pytest -q \
  apps/control_plane/tests/integration/session_objectives/test_objective_projector_flow.py \
  apps/control_plane/tests/integration/session_completion/test_session_completed_worker_flow.py \
  apps/control_plane/tests/integration/http/test_get_session_metadata.py
```

Run frontend completion-indicator tests:

```bash
cd apps/frontend
pnpm exec vitest run \
  src/pages/session/components/SessionCompletionIndicator.test.tsx \
  src/pages/SessionPage.completion.test.tsx
```

## Manual Verification Flow

1. Create a lab session and note `session_id`.
2. Trigger all required objectives for that lab/session.
3. Verify a single `session.completed.v1` outbox row exists for the session.
4. Replay/reprocess objective/completion workers.
5. Verify completion fields remain unchanged:
   - `completion_status`
   - `completed_at`
   - `completion_reason_code`
6. Call metadata endpoint twice and verify completion fields are stable.
7. Refresh/reconnect frontend session page and verify completion indicator matches metadata.

## Example API Check

```bash
curl -sS \
  -H "Authorization: Bearer local:owner-user" \
  http://localhost:8000/api/v1/sessions/<session_id> | jq '.session | {
    completion_status,
    completed_at,
    completion_reason_code
  }'
```

## Expected Results

- Completion event is emitted once for the first terminal completion transition.
- Replay does not create duplicate completion mutation.
- Metadata endpoint returns persisted completion values across refresh/reconnect.
- Frontend indicator reflects backend metadata only.
