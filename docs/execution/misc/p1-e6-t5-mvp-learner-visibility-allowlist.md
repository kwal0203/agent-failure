# P1-E6-T5 MVP Learner-Visibility Allowlist

## Purpose

Define the MVP server-side allowlist for learner-visible trace retrieval.

This document is intentionally identity-independent. It defines **what event types are eligible** for learner projection, not **who is allowed to read a session**.

## Scope

- In scope:
  - Event-type allowlist for learner-visible trace projection.
  - Deny-by-default behavior for non-allowlisted events.
- Out of scope:
  - Object-level authorization and identity/role enforcement.
  - Advanced replay/cursor pagination semantics.
  - Payload redaction hardening beyond basic MVP shaping.

## MVP Policy

- Projection policy is centralized server-side.
- Only explicitly allowlisted events are returned by learner trace retrieval.
- Any event not allowlisted is treated as internal-only and excluded.
- Policy is independent of principal identity in this phase.

## Allowlisted Event Types (MVP)

1. `learner.USER_PROMPT_SUBMITTED`
2. `model.MODEL_TURN_COMPLETED`
3. `model.MODEL_TURN_FAILED`

## Denied by Default (MVP)

- All `lifecycle.*` events.
- All `runtime.*` events.
- All `tool.*` events.
- Non-allowlisted `model.*` events (for example `MODEL_TURN_STARTED`).

## Contract Notes for P1-E6-T5

- Retrieval paths must apply this projection consistently.
- Projection logic should be testable in isolation (allow/deny examples).
- Authz remains a separate concern and should continue to be enforced by existing session ownership/admin checks in route/service layers.

## Follow-On Work (Post-MVP)

- Evolve projection to identity-aware policy (`P2-E6-T8`) while keeping rules centralized and auditable.
- Extend payload shaping/redaction policy if additional event types become learner-visible.
