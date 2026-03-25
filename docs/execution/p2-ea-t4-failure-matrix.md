# P2-EA-T4 Failure Matrix and Desired Behavior

## Scope
This matrix defines baseline error handling expectations for the session create/provision/stream path so failures are explicit, user-safe, and diagnosable.

## Standard log envelope (all cases)
Every failure log should include at minimum:
- `event`: stable machine-readable event name
- `session_id`
- `user_id` (or principal id)
- `lab_id` (if known)
- `stage`: `create_session` | `provisioning` | `stream_turn`
- `error_code`: internal code used by API/events
- `retryable`: boolean
- `timestamp`
- `trace_id` / `request_id` (if available)

## Failure matrix

| Case | Detection point | User-visible message | Retryable | Server log fields (in addition to standard envelope) |
|---|---|---|---|---|
| Create-session succeeds but provisioning worker not running | Session remains `PROVISIONING` beyond expected warmup window; no recent provisioning worker tick | "Your session is still starting. This is taking longer than expected. Please retry in a moment." | Yes | `event=session_provisioning_stalled`, `session_state=PROVISIONING`, `provisioning_age_seconds`, `last_worker_tick_at` (nullable), `worker_name=provisioning_worker` |
| Provisioning fails (`K8S_APPLY_FAILED`, image pull/start error) | Provisioning transition/event marks failure (or K8s status indicates pull/start failure) | "We couldn’t start the lab runtime. Please retry. If this continues, contact support." | Yes | `event=session_provisioning_failed`, `failure_reason` (`K8S_APPLY_FAILED`/`IMAGE_PULL_BACKOFF`/`START_ERROR`), `k8s_namespace`, `pod_name`, `container_status_reason`, `image_ref`, `k8s_event_excerpt` |
| Websocket turn fails before first chunk | Turn accepted, but stream errors before first assistant token/chunk emitted | "The assistant failed before responding. Please resend your prompt." | Yes | `event=turn_failed_before_first_chunk`, `turn_id` (if available), `time_to_failure_ms`, `provider`, `model`, `ws_connected=true`, `first_chunk_emitted=false` |
| Provider timeout/error mid-turn | At least one chunk emitted, then provider timeout/upstream error occurs | "The response was interrupted. You can retry to continue." | Yes | `event=turn_failed_mid_stream`, `turn_id`, `time_to_first_chunk_ms`, `chunks_emitted`, `provider`, `model`, `upstream_error_type`, `timeout_ms` (if timeout), `first_chunk_emitted=true` |

## Behavior rules
- Never leave turns indefinitely in `TURN_IN_PROGRESS`; always finalize to a terminal state on error.
- Preserve partial output for mid-turn failures when possible; do not discard already-streamed content.
- Emit stable `error_code` values so frontend messaging can map consistently.
- Keep retry guidance user-facing and simple; keep diagnostics server-side.

## Suggested internal error codes
- `SESSION_PROVISIONING_STALLED`
- `SESSION_PROVISIONING_FAILED`
- `TURN_FAILED_BEFORE_FIRST_CHUNK`
- `TURN_FAILED_MID_STREAM`
