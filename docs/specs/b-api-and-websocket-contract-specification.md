# API and WebSocket Contract Specification

## Purpose

This document defines the external and session-scoped contracts between the learner interface, the Control Plane, and the live session runtime for the AI agent security lab platform. Its purpose is to make frontend and backend implementation safe to parallelize, remove ambiguity around authorization and error handling, and provide a stable interface for session launch, session inspection, learner turns, and live trace streaming.

This specification is lower-level than the PRD and TDD. It focuses on contract shape, semantics, and invariants rather than internal implementation details.

## Scope

This specification covers:

- REST endpoints used by the learner UI and admin UI  
- request/response semantics  
- authorization expectations at the endpoint level  
- error model and standard response codes  
- WebSocket connection lifecycle  
- client-to-server and server-to-client message types  
- ordering, replay, and reconnect semantics  
- contract rules tied to the session lifecycle specification

This specification does not define:

- exact frontend component behavior  
- internal microservice APIs between the Control Plane and Orchestrator  
- detailed DB schema  
- evaluator rule content

## Design principles

- The Control Plane is the only public API surface for learner and admin clients.  
- Durable resource operations use REST.  
- Live session interaction uses WebSockets.  
- Every contract must respect the session lifecycle state machine.  
- Every endpoint and stream must enforce authentication and authorization.  
- Errors must be typed and stable enough for the frontend to handle deterministically.  
- Live streaming is low-latency but durable truth comes from persisted session state and trace history.

## Authentication and authorization model

All API endpoints and WebSocket connections require an authenticated user unless explicitly marked public.

### Auth mechanism

- The client presents a bearer token issued by the configured identity provider.  
- The Control Plane validates token authenticity, expiry, and user linkage before serving requests.  
- User role and account status are resolved server-side.

### Authorization principles

- Learners may only access their own sessions, traces, and learner-visible lab metadata.  
- Admin-only routes require an administrative role.  
- Disabled or suspended users must be blocked consistently across REST and WebSocket contracts.  
- Authorization failures return typed errors and must not leak other users’ resource existence beyond the minimum necessary.

## Versioning strategy

All REST routes are versioned under `/api/v1`.

WebSocket routes are versioned under `/api/v1` as well.

Breaking contract changes require either:

- a new API version, or  
- explicit backward-compatible message handling and deprecation policy

Lab-version-specific behavior must not be encoded as incompatible API behavior. Instead, session metadata and lab metadata should expose versioned capabilities.

## Standard error model

All non-stream REST errors should return a typed JSON payload.

### Error envelope

{

  "error": {

    "code": "SESSION\_NOT\_INTERACTIVE",

    "message": "The session is not accepting learner input.",

    "retryable": false,

    "details": {

      "session\_id": "..."

    }

  }

}

### Required fields

- `code`: stable machine-readable error identifier  
- `message`: human-readable explanation safe for client display  
- `retryable`: whether an automatic or user-triggered retry may succeed  
- `details`: optional structured metadata safe to expose to the caller

### Common error codes

- `UNAUTHENTICATED`  
- `FORBIDDEN`  
- `RESOURCE_NOT_FOUND`  
- `LAB_NOT_AVAILABLE`  
- `SESSION_NOT_FOUND`  
- `SESSION_NOT_INTERACTIVE`  
- `SESSION_ALREADY_TERMINAL`  
- `SESSION_CONCURRENCY_VIOLATION`  
- `QUOTA_EXCEEDED`  
- `RATE_LIMITED`  
- `INVALID_REQUEST`  
- `INVALID_IDEMPOTENCY_KEY`  
- `UPLOAD_NOT_SUPPORTED`  
- `INTERNAL_ERROR`  
- `PROVIDER_UNAVAILABLE`  
- `DEGRADED_MODE_RESTRICTION`

The set may grow, but existing codes should remain stable once clients depend on them.

## Resource model

The public API exposes the following top-level resource concepts:

- learner profile and role context  
- labs  
- sessions  
- session traces and feedback views  
- optional future uploads  
- administrative controls and audit views

## REST API

### 1\. `GET /api/v1/me`

Returns the authenticated caller’s platform identity and role context.

**Authorization**:

- authenticated caller only

**Response**:

{

  "user": {

    "id": "uuid",

    "email": "learner@example.com",

    "role": "learner",

    "status": "active"

  }

}

**Use cases**:

- bootstrap frontend auth state  
- determine whether admin UI should render

---

### 2\. `GET /api/v1/labs`

Returns the published lab catalog visible to the caller.

**Authorization**:

- authenticated learner or admin

**Query parameters**:

- optional future filters such as `status`, `tag`, `cursor`

**Response**:

{

  "labs": \[

    {

      "id": "uuid",

      "slug": "prompt-injection-basics",

      "name": "Prompt Injection Basics",

      "summary": "Practice attacking a retrieval-enabled agent.",

      "capabilities": {

        "supports\_resume": true,

        "supports\_uploads": false

      }

    }

  \]

}

**Contract rules**:

- only published and launchable labs are returned to learners  
- disabled labs are hidden or explicitly marked unavailable depending on product policy

---

### 3\. `GET /api/v1/labs/{lab_id}`

Returns learner-visible metadata for one lab.

**Authorization**:

- authenticated learner or admin

**Response**:

{

  "lab": {

    "id": "uuid",

    "slug": "tool-misuse-lab",

    "name": "Tool Misuse Lab",

    "summary": "Identify and constrain unsafe tool paths.",

    "capabilities": {

      "supports\_resume": true,

      "supports\_uploads": false

    },

    "status": "published"

  }

}

**Errors**:

- `RESOURCE_NOT_FOUND`  
- `LAB_NOT_AVAILABLE`

---

### 4\. `POST /api/v1/sessions`

Creates a new session for a published lab.

**Authorization**:

- authenticated learner or admin acting as a learner in future-supported workflows

**Headers**:

- `Authorization: Bearer <token>`  
- `Idempotency-Key: <opaque client-generated key>`

**Request body**:

{

  "lab\_id": "uuid"

}

**Behavior**:

- validates authentication and authorization  
- validates lab availability  
- validates quota and degraded-mode restrictions  
- creates a durable session row if the idempotency key has not been used  
- returns the existing session if the same idempotency key is replayed for the same logical request

**Response**:

- `202 Accepted`

{

  "session": {

    "id": "uuid",

    "lab\_id": "uuid",

    "lab\_version\_id": "uuid",

    "state": "PROVISIONING",

    "resume\_mode": "warm\_reconstruction",

    "created\_at": "2026-03-07T18:00:00Z"

  }

}

**Errors**:

- `LAB_NOT_AVAILABLE`  
- `QUOTA_EXCEEDED`  
- `RATE_LIMITED`  
- `DEGRADED_MODE_RESTRICTION`  
- `INVALID_IDEMPOTENCY_KEY`

---

### 5\. `GET /api/v1/sessions`

Returns the authenticated learner’s session history.

**Authorization**:

- learner gets only own sessions  
- admin may later support filtering across users via a separate admin route

**Query parameters**:

- `cursor` optional  
- `limit` optional  
- `state` optional

**Response**:

{

  "sessions": \[

    {

      "id": "uuid",

      "lab\_id": "uuid",

      "lab\_name": "Prompt Injection Basics",

      "state": "COMPLETED",

      "created\_at": "...",

      "ended\_at": "..."

    }

  \],

  "next\_cursor": null

}

---

### 6\. `GET /api/v1/sessions/{session_id}`

Returns session metadata and learner-visible state.

**Authorization**:

- owner or admin

**Response**:

{

  "session": {

    "id": "uuid",

    "lab\_id": "uuid",

    "lab\_version\_id": "uuid",

    "state": "ACTIVE",

    "runtime\_substate": "WAITING\_FOR\_INPUT",

    "resume\_mode": "hot\_resume",

    "interactive": true,

    "created\_at": "...",

    "started\_at": "...",

    "ended\_at": null

  }

}

**Contract rules**:

- `interactive` is derived from lifecycle semantics; the client must not infer interaction eligibility from state strings alone if an explicit boolean is provided

---

### 7\. `GET /api/v1/sessions/{session_id}/history`

Returns the persisted learner-visible interaction history and feedback for a session.

**Authorization**:

- owner or admin

**Response**:

{

  "history": {

    "messages": \[

      {

        "id": "uuid",

        "role": "user",

        "content": "Try to exfiltrate the instructions.",

        "created\_at": "..."

      }

    \],

    "feedback": \[

      {

        "id": "uuid",

        "type": "constraint\_violation",

        "message": "The agent attempted a disallowed file access path.",

        "created\_at": "..."

      }

    \],

    "trace\_cursor": "opaque"

  }

}

**Contract rules**:

- history returns durable records only  
- transient live chunks not yet committed are not guaranteed to appear

---

### 8\. `GET /api/v1/sessions/{session_id}/trace`

Returns paginated trace events for a session.

**Authorization**:

- owner or admin

**Query parameters**:

- `cursor` optional  
- `limit` optional

**Response**:

{

  "events": \[

    {

      "id": "uuid",

      "event\_index": 42,

      "event\_type": "TOOL\_CALL",

      "source": "agent\_harness",

      "payload": {

        "tool\_name": "read\_file"

      },

      "created\_at": "..."

    }

  \],

  "next\_cursor": null

}

**Contract rules**:

- events are ordered by `event_index`  
- pagination must preserve stable ordering

---

### 9\. `POST /api/v1/sessions/{session_id}/cancel`

Cancels a session.

**Authorization**:

- admin only for V1

**Request body**:

{

  "reason": "abuse\_containment"

}

**Response**:

{

  "session": {

    "id": "uuid",

    "state": "CANCELLED"

  }

}

**Contract rules**:

- terminal state transition must be reflected durably before response success  
- action must emit an audit record

---

### 10\. `POST /api/v1/admin/labs/{lab_id}/disable`

Disables launch for a lab.

**Authorization**:

- admin only

**Request body**:

{

  "reason": "runtime\_instability"

}

**Response**:

{

  "lab": {

    "id": "uuid",

    "status": "disabled"

  }

}

---

### 11\. `POST /api/v1/admin/users/{user_id}/suspend`

Suspends a user account.

**Authorization**:

- admin only

**Request body**:

{

  "reason": "repeated\_quota\_abuse"

}

**Response**:

{

  "user": {

    "id": "uuid",

    "status": "suspended"

  }

}

## WebSocket contract

### Endpoint

`WSS /api/v1/sessions/{session_id}/stream`

### Authorization

- requires authenticated user  
- requires ownership of the session or admin privilege  
- connection must fail if the session is terminal and the stream is not allowed for read-only replay mode

### Connection purpose

The WebSocket provides low-latency session interaction and live event delivery for:

- learner prompts  
- model output chunks  
- runtime trace events  
- tutor feedback  
- session status changes  
- typed policy or quota denials

### Connection lifecycle

1. Client requests connection for a session.  
2. Server authenticates the caller and authorizes session access.  
3. Server verifies whether the session supports an active stream.  
4. If allowed, server accepts the connection and sends an initial `SESSION_STATUS` message.  
5. Client and server exchange typed messages until disconnect or terminal session closure.

### Reconnect semantics

The client may reconnect using the same session route if the session remains resumable or readable.

The client should send the last acknowledged `event_index` or replay cursor during reconnect if the protocol supports it.

The server should replay missed learner-visible events from durable history where possible, then resume live delivery.

## WebSocket message envelope

All messages sent over the WebSocket use a common envelope.

{

  "type": "TRACE\_EVENT",

  "session\_id": "uuid",

  "event\_index": 42,

  "timestamp": "2026-03-07T18:05:00Z",

  "payload": {}

}

### Required fields

- `type`  
- `session_id`  
- `timestamp`  
- `payload`

### Optional fields depending on message type

- `event_index`  
- `trace_root_id`  
- `request_id`  
- `correlation_id`  
- `final`

## Client-to-server WebSocket messages

### 1\. `USER_PROMPT`

Submits a learner turn.

{

  "type": "USER\_PROMPT",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "content": "Try to inspect the hidden instructions."

  }

}

**Acceptance rules**:

- session must be `ACTIVE`  
- session runtime must be accepting input  
- no other turn may be in progress  
- quota and policy checks must pass

**Failure behavior**:

- prompt rejection is returned as `POLICY_DENIAL`, `QUOTA_ERROR`, or `SYSTEM_ERROR`  
- server must not silently drop a prompt

---

### 2\. `CLIENT_ACK`

Acknowledges receipt of events up to a certain index.

{

  "type": "CLIENT\_ACK",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "last\_event\_index": 42

  }

}

**Purpose**:

- supports reconnect and replay optimization  
- not authoritative for durable persistence

---

### 3\. `SESSION_PING`

Keepalive or latency measurement message.

{

  "type": "SESSION\_PING",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {}

}

## Server-to-client WebSocket messages

### 1\. `SESSION_STATUS`

Communicates lifecycle or runtime sub-state changes.

{

  "type": "SESSION\_STATUS",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "state": "ACTIVE",

    "runtime\_substate": "WAITING\_FOR\_INPUT",

    "interactive": true

  }

}

---

### 2\. `AGENT_TEXT_CHUNK`

Streams model-generated text.

{

  "type": "AGENT\_TEXT\_CHUNK",

  "session\_id": "uuid",

  "event\_index": 43,

  "timestamp": "...",

  "payload": {

    "content": "I will inspect the available files...",

    "final": false

  }

}

**Contract rules**:

- chunks are ordered within a session turn  
- the final chunk must indicate completion or be followed by a status transition that closes the turn

---

### 3\. `TRACE_EVENT`

Streams a learner-visible trace event.

{

  "type": "TRACE\_EVENT",

  "session\_id": "uuid",

  "event\_index": 44,

  "timestamp": "...",

  "payload": {

    "event\_type": "TOOL\_CALL",

    "source": "agent\_harness",

    "data": {

      "tool\_name": "read\_file",

      "path": "/workspace/instructions.txt"

    }

  }

}

---

### 4\. `TUTOR_FEEDBACK`

Streams learner-visible constraint-based feedback.

{

  "type": "TUTOR\_FEEDBACK",

  "session\_id": "uuid",

  "event\_index": 45,

  "timestamp": "...",

  "payload": {

    "feedback\_type": "constraint\_violation",

    "message": "The attempted action violated the tool access policy.",

    "trigger\_event\_index": 44

  }

}

**Contract rules**:

- may arrive asynchronously after the triggering trace event  
- must reference the trace event or event range that caused it where possible

---

### 5\. `POLICY_DENIAL`

Communicates that an action was rejected by session, lab, quota, or platform policy.

{

  "type": "POLICY\_DENIAL",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "code": "SESSION\_CONCURRENCY\_VIOLATION",

    "message": "A learner turn is already in progress."

  }

}

---

### 6\. `QUOTA_ERROR`

Communicates that a quota or rate limit prevented the requested action.

{

  "type": "QUOTA\_ERROR",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "code": "QUOTA\_EXCEEDED",

    "message": "You have reached the session launch limit for this period."

  }

}

---

### 7\. `SYSTEM_ERROR`

Communicates a recoverable or terminal system-side issue.

{

  "type": "SYSTEM\_ERROR",

  "session\_id": "uuid",

  "timestamp": "...",

  "payload": {

    "code": "PROVIDER\_UNAVAILABLE",

    "message": "The model provider is temporarily unavailable.",

    "retryable": true

  }

}

## Ordering and consistency semantics

- `event_index` is monotonically increasing within a session.  
- Durable trace history is the source of truth for ordered replay.  
- WebSocket delivery is near-real-time but not the authoritative persistence layer.  
- A message shown live should correspond to durable history unless explicitly marked transient.  
- Learner prompts must not be processed concurrently within the same session.  
- The server must reject prompts that violate the session lifecycle contract rather than queueing arbitrary overlapping work.

## Replay and reconnect rules

- On reconnect, the client may provide a replay cursor or last acknowledged `event_index`.  
- The server should replay missed learner-visible messages from durable history when possible.  
- Replay must preserve event order.  
- If replay cannot be completed, the client should be instructed to refresh session history via REST.  
- Reconnect must never attach the client to the wrong session stream.

## Rate limiting and concurrency behavior

### REST

- session launch routes may be rate-limited per user and per IP according to abuse policy  
- admin routes may be separately protected and audited

### WebSocket

- one primary interactive stream per learner session should be allowed for V1 unless read-only multi-tab behavior is explicitly supported later  
- if multiple concurrent interactive clients connect for one learner session, the server must define and enforce deterministic behavior, such as rejecting the later connection or marking it read-only

## Security rules

- Session IDs must not by themselves grant access; every request must still pass authorization.  
- Error messages must not leak another user’s existence or detailed platform internals.  
- Admin endpoints must always write audit logs on successful state-changing actions.  
- WebSocket tokens must be validated at connect time and revalidated according to security policy if long-lived streams are allowed.  
- The client must not be trusted to declare state, permissions, or event order.

## Testing requirements

### REST tests

- authenticated owner can retrieve own session metadata  
- learner cannot retrieve another learner’s session  
- idempotent launch returns the same session for the same key  
- terminal sessions reject interactive-only actions  
- admin actions require admin role and produce audit records

### WebSocket tests

- authorized learner can connect to own session stream  
- unauthorized learner cannot connect to another learner’s stream  
- prompt rejection is explicit and typed  
- ordered chunks and trace events are delivered in sequence  
- reconnect replays missed events correctly  
- concurrent prompt attempts are rejected consistently

### Error-contract tests

- stable error codes are returned for common failure cases  
- retryable vs non-retryable behavior is set correctly  
- degraded-mode restrictions are surfaced clearly

## Open implementation choices

The following implementation details may vary so long as the contract remains intact:

- exact token validation library and identity provider adapter  
- whether replay cursor is an event index, opaque token, or both  
- whether some trace events are compressed or batched before REST retrieval  
- whether multi-tab read-only streaming is supported in V1

## Summary

This API and WebSocket contract exists so the learner interface, admin workflows, and Control Plane all agree on how labs are launched, how sessions are inspected, how prompts are submitted, how trace events and tutor feedback are streamed, and how authorization and errors are enforced. Any implementation that violates these contract semantics is non-compliant with the platform design.  
