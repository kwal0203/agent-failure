# Current Plan: Lab 1 Tiered Runtime Wiring (Easy/Medium)

## Context
Lab 1 has an end-to-end MVP loop, but difficulty tiering is not yet runtime-wired.
This plan covers only the runtime wiring needed to ship Easy/Medium with Medium default.

## Goal
Implement tier-aware session/runtime/evaluator wiring while keeping attacker console and victim chat behavior unchanged.

## Ticket List
1. `LAB1-TIER-WIRE-1` Add durable active tier to session model and APIs
2. `LAB1-TIER-WIRE-2` Accept and validate active tier during session creation
3. `LAB1-TIER-WIRE-3` Propagate active tier through provisioning and runtime env
4. `LAB1-TIER-WIRE-4` Load runtime prompt/policy from active tier
5. `LAB1-TIER-WIRE-5` Propagate active tier into evaluator routing payload
6. `LAB1-TIER-WIRE-6` Add backward-compat defaults and guardrails
7. `LAB1-TIER-WIRE-7` Add wiring tests (control-plane, runtime, evaluator)

## Ticket Details

### `LAB1-TIER-WIRE-1` Add durable active tier to session model and APIs
- Scope:
  - Add `active_tier` column to `sessions` (`easy|medium`), default `medium`.
  - Expose `active_tier` in create-session result and session metadata response.
- Files:
  - `alembic/versions/*_add_active_tier_to_sessions.py` (new migration)
  - `apps/control_plane/src/infrastructure/persistence/models.py`
  - `apps/control_plane/src/application/session_create/schemas.py`
  - `apps/control_plane/src/application/session_query/types.py`
  - `apps/control_plane/src/interfaces/http/schemas.py`
  - `apps/control_plane/src/infrastructure/persistence/session_repository.py`
- Acceptance criteria:
  - New sessions persist `active_tier=medium` when unspecified.
  - `POST /api/v1/sessions` response includes `session.active_tier`.
  - `GET /api/v1/sessions/{id}` response includes `session.active_tier`.

### `LAB1-TIER-WIRE-2` Accept and validate active tier during session creation
- Scope:
  - Add optional `active_tier` to create-session request.
  - Validate allowlist (`easy`, `medium`) and reject invalid values.
  - Persist chosen tier into session row.
- Files:
  - `apps/control_plane/src/interfaces/http/schemas.py`
  - `apps/control_plane/src/interfaces/http/main.py`
  - `apps/control_plane/src/application/session_create/service.py`
  - `apps/control_plane/src/application/session_create/ports.py`
  - `apps/control_plane/src/infrastructure/persistence/session_repository.py`
  - `apps/frontend/src/pages/LabsPage.tsx`
- Acceptance criteria:
  - `active_tier` omitted => medium.
  - `active_tier=easy|medium` accepted and persisted.
  - invalid tier returns 400 with deterministic error code.

### `LAB1-TIER-WIRE-3` Propagate active tier through provisioning and runtime env
- Scope:
  - Include `active_tier` in create-session outbox payload.
  - Carry `active_tier` in `RuntimeProvisionRequest.metadata`.
  - Set runtime pod env var `LAB_ACTIVE_TIER=<tier>`.
- Files:
  - `apps/control_plane/src/infrastructure/persistence/outbox_create_session.py`
  - `apps/control_plane/src/application/orchestrator/service.py`
  - `apps/control_plane/src/application/orchestrator/types.py`
  - `apps/control_plane/src/infrastructure/orchestrator/k8s_provisioner.py`
- Acceptance criteria:
  - Claimed provisioning event has `active_tier`.
  - Runtime pod manifest includes `LAB_ACTIVE_TIER`.
  - Missing tier in older payloads safely defaults to medium.

### `LAB1-TIER-WIRE-4` Load runtime prompt/policy from active tier
- Scope:
  - Add tier config (easy/medium) for prompt policy in runtime/harness.
  - Context builder chooses prompt pack from `LAB_ACTIVE_TIER`.
  - Keep attacker console and victim chat flow unchanged.
- Files:
  - `apps/agent_harness/src/infrastructure/lab_context/local_v1.py`
  - `apps/agent_harness/src/interfaces/runtime/dependencies.py` (if needed for injection)
  - `runtimes/baseline/service.py` (only if turn/event payload wiring needs tier visibility)
  - `runtimes/baseline/labs/prompt_injection.py` (or new tier config module)
- Acceptance criteria:
  - Easy and Medium produce different system prompt behavior.
  - Chat and inbox UX/API contracts unchanged.
  - Runtime defaults to medium when env not set.

### `LAB1-TIER-WIRE-5` Propagate active tier into evaluator routing payload
- Scope:
  - Include `active_tier` in evaluator enqueue payload.
  - Thread through evaluator task parsing and bundle/rule routing surface.
  - Keep current evaluator behavior stable if tier absent.
- Files:
  - `apps/control_plane/src/infrastructure/persistence/outbox.py`
  - `apps/control_plane/src/application/trace/service.py`
  - `apps/evaluator/src/infrastructure/outbox_evaluator_repository.py`
  - `apps/evaluator/src/application/types.py`
  - `apps/evaluator/src/application/service.py`
  - `apps/evaluator/src/application/rules/registry.py`
- Acceptance criteria:
  - Evaluator worker can read tier from payload.
  - Tier value is available in rule resolution inputs.
  - No regression for sessions/events without tier.

### `LAB1-TIER-WIRE-6` Add backward-compat defaults and guardrails
- Scope:
  - Centralize tier parsing/normalization with safe default (`medium`).
  - Avoid hard failures on older rows/events missing tier.
  - Add structured logging fields for `active_tier` on create/provision/evaluate flows.
- Files:
  - `apps/control_plane/src/application/session_create/service.py`
  - `apps/control_plane/src/application/orchestrator/service.py`
  - `apps/evaluator/src/interfaces/runtime/evaluator_worker.py`
  - `apps/evaluator/src/infrastructure/outbox_evaluator_repository.py`
- Acceptance criteria:
  - Legacy sessions keep functioning without migration backfills.
  - Logs include active tier where available.
  - Invalid tier strings are normalized/rejected at ingress.

### `LAB1-TIER-WIRE-7` Add wiring tests (control-plane, runtime, evaluator)
- Scope:
  - Session create tests for tier defaults + validation.
  - Provisioning flow tests asserting tier in outbox->manifest path.
  - Runtime tests asserting tier-specific prompt selection.
  - Evaluator tests asserting tier reaches routing input.
- Files:
  - `apps/control_plane/tests/integration/http/test_create_session.py`
  - `apps/control_plane/tests/application/orchestrator/test_orchestrator_service.py`
  - `apps/control_plane/tests/infrastructure/orchestrator/test_k8s_provisioner_manifest.py`
  - `runtimes/baseline/tests/test_runtime_stream_endpoint.py`
  - `apps/evaluator/tests/test_evaluator_worker.py`
  - `apps/evaluator/tests/test_prompt_injection_rules_and_registry.py`
- Acceptance criteria:
  - All new tests pass locally.
  - Existing test suites for create/provision/runtime/evaluator remain green.

## Execution Order
1. `LAB1-TIER-WIRE-1`
2. `LAB1-TIER-WIRE-2`
3. `LAB1-TIER-WIRE-3`
4. `LAB1-TIER-WIRE-4`
5. `LAB1-TIER-WIRE-5`
6. `LAB1-TIER-WIRE-6`
7. `LAB1-TIER-WIRE-7`

## Definition of Done
- Easy/Medium tier is persisted per session run and queryable.
- Runtime policy prompt is selected by active tier with medium default.
- Evaluator path receives active tier context without breaking legacy flows.
- Frontend can launch sessions with explicit tier selection.
- Tests cover default, explicit tier, and backward-compat behavior.
